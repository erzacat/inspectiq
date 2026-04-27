# Databricks notebook source
# MAGIC %md
# MAGIC # InspectIQ — MLflow Evaluation (Traces → Expectations → Dataset → Judges)
# MAGIC
# MAGIC Native Agent Bricks evaluation flow:
# MAGIC 1. **Start from existing traces** in the supervisor's dev experiment
# MAGIC 2. **Attach expectations** (ground truth) to traces we care about
# MAGIC 3. **Create a UC eval dataset** from the annotated traces
# MAGIC 4. **Define scorers** — built-in Correctness + Safety + Guidelines, plus a custom tool-routing judge
# MAGIC 5. **Run `mlflow.genai.evaluate()`** against the dataset
# MAGIC
# MAGIC **Endpoint:** `mas-0975bb2f-endpoint`
# MAGIC **Experiment:** `2776229023959006` (`/Users/emily.liu@databricks.com/mas-0975bb2f-dev-experiment`)
# MAGIC **Eval dataset UC table:** `mbi_demo.inspectiq.supervisor_eval_v1`

# COMMAND ----------

# MAGIC %pip install --quiet --upgrade "mlflow>=3.0" "databricks-agents" databricks-sdk pandas
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import mlflow
import pandas as pd

ENDPOINT      = "mas-0975bb2f-endpoint"
EXPERIMENT_ID = "2776229023959006"
EVAL_TABLE    = "mbi_demo.inspectiq.supervisor_eval_v1"
LLM_JUDGE     = "databricks-claude-sonnet-4-5"

mlflow.set_experiment(experiment_id=EXPERIMENT_ID)
print(f"Experiment: {EXPERIMENT_ID}")

# COMMAND ----------
# MAGIC %md ## Step 1 — Ground-truth map (question → expected answer + tool path)
# MAGIC
# MAGIC Curated by hand. These are the expectations we attach to the existing traces.

# COMMAND ----------

GROUND_TRUTH = {
    "Were any immediate safety risks identified in the parking garage inspections?": {
        "expected_response": "Yes. Column C-14 in the Commerce Center Parking Garage (INS-SS-002) has exposed rebar with active corrosion and ~31% section loss, requiring immediate shoring within 24 hours and partial closure of Level 3.",
        "expected_tool": "rag",
        "difficulty": "easy",
    },
    "What corrective actions were recommended for concrete deterioration?": {
        "expected_response": "Corrective actions include epoxy crack injection, patch repair, protective sealant application, and in critical cases temporary shoring and reencasement (INS-CO-001, INS-CO-002).",
        "expected_tool": "rag",
        "difficulty": "medium",
    },
    "What structural issues were identified in the Parker Street Highway Overpass?": {
        "expected_response": "INS-SS-001 identified section loss on fascia girders, fatigue cracking at web-to-flange welds, paint system failure, and bearing corrosion.",
        "expected_tool": "rag",
        "difficulty": "easy",
    },
    "Which asphalt projects have alligator cracking?": {
        "expected_response": "Valley Forge Industrial Park Access Roads (INS-AP-003) reported alligator cracking over ~40% of the surface; recommended action is full-depth reclamation.",
        "expected_tool": "rag",
        "difficulty": "medium",
    },
    "What is the total estimated repair cost by inspection type?": {
        "expected_response": "Total estimated_repair_cost grouped by inspection_type. Asphalt has the highest total, followed by Concrete and Structural Steel.",
        "expected_tool": "sql",
        "difficulty": "easy",
    },
    "Show me all safety-flagged projects sorted by priority score.": {
        "expected_response": "Projects where safety_flagged=true, ordered by priority_score descending. Includes INS-SS-002, INS-CO-001, INS-AP-001, INS-AP-002, INS-AP-003.",
        "expected_tool": "sql",
        "difficulty": "easy",
    },
    "Which projects in Pennsylvania are overdue for inspection?": {
        "expected_response": "Filter state='PA' and overdue=true, sorted by days_overdue descending.",
        "expected_tool": "sql",
        "difficulty": "medium",
    },
    "What is the average condition rating for each state?": {
        "expected_response": "Group project_assets by state and compute AVG(condition_rating).",
        "expected_tool": "sql",
        "difficulty": "easy",
    },
    "How many projects in Pennsylvania have a Poor or Critical condition rating?": {
        "expected_response": "Count of project_assets where state='PA' AND condition_category IN ('Poor','Critical'). Expected answer is 6.",
        "expected_tool": "sql",
        "difficulty": "easy",
    },
    "Which Pennsylvania projects have safety flags and what were the specific issues found?": {
        "expected_response": "From DB: INS-SS-002, INS-AP-001, INS-AP-002, INS-AP-003 are PA safety-flagged. From reports: INS-SS-002 exposed rebar at C-14; INS-AP-002 pothole clusters; INS-AP-003 severe alligator cracking.",
        "expected_tool": "both",
        "difficulty": "hard",
    },
    "What are the most expensive projects to repair and what deficiencies drove those costs?": {
        "expected_response": "From DB: I-78 Eastbound (INS-AP-002, ~$6.2M) and I-95 Bridge Deck (INS-CO-001, ~$3.0M) are highest. From reports: INS-AP-002 has block cracking and base failure; INS-CO-001 has deck delamination and scour-critical conditions.",
        "expected_tool": "both",
        "difficulty": "hard",
    },
    "What is the weather forecast for Pittsburgh?": {
        "expected_response": "Out of scope. System should gracefully decline and explain it only answers MBI inspection questions.",
        "expected_tool": "none",
        "difficulty": "easy",
    },
}
print(f"Ground truth: {len(GROUND_TRUTH)} questions")

# COMMAND ----------
# MAGIC %md ## Step 2 — Pull the existing traces and attach expectations

# COMMAND ----------

traces_df = mlflow.search_traces(
    experiment_ids=[EXPERIMENT_ID],
    max_results=50,
    order_by=["timestamp_ms DESC"],
)
print(f"Fetched {len(traces_df)} traces")
traces_df.head(3)

# COMMAND ----------

# Match each trace to a question (by request text) and log expectations
from mlflow.entities import AssessmentSource, AssessmentSourceType

matched = 0
for _, row in traces_df.iterrows():
    request_text = row.get("request")
    if not isinstance(request_text, str):
        continue

    # Normalize — the trace request comes in with leading whitespace sometimes
    q_clean = request_text.strip()
    for gt_question, gt in GROUND_TRUTH.items():
        if gt_question.lower() in q_clean.lower() or q_clean.lower() in gt_question.lower():
            trace_id = row["trace_id"]
            try:
                mlflow.log_expectation(
                    trace_id=trace_id,
                    name="expected_response",
                    value=gt["expected_response"],
                    source=AssessmentSource(source_type=AssessmentSourceType.HUMAN, source_id="emily.liu@databricks.com"),
                )
                mlflow.log_expectation(
                    trace_id=trace_id,
                    name="expected_tool",
                    value=gt["expected_tool"],
                    source=AssessmentSource(source_type=AssessmentSourceType.HUMAN, source_id="emily.liu@databricks.com"),
                )
                matched += 1
                print(f"  Tagged trace {trace_id[:30]}... -> {gt['expected_tool']}")
            except Exception as e:
                print(f"  Error on {trace_id[:30]}: {e}")
            break

print(f"\nAttached expectations to {matched} traces.")

# COMMAND ----------
# MAGIC %md ## Step 3 — Create a UC eval dataset from the annotated traces

# COMMAND ----------

from mlflow.genai import datasets

# Create (or get) the eval dataset — UC-backed, versioned
try:
    dataset = datasets.create_dataset(uc_table_name=EVAL_TABLE)
    print(f"Created eval dataset: {EVAL_TABLE}")
except Exception as e:
    # Already exists -> load it
    dataset = datasets.get_dataset(uc_table_name=EVAL_TABLE)
    print(f"Loaded existing eval dataset: {EVAL_TABLE}")

# COMMAND ----------

# Build records: one per question with inputs + expectations
records = []
for q, gt in GROUND_TRUTH.items():
    records.append({
        "inputs": {"question": q},
        "expectations": {
            "expected_response": gt["expected_response"],
            "expected_tool": gt["expected_tool"],
        },
        "tags": {"difficulty": gt["difficulty"]},
    })

dataset.merge_records(records)
print(f"Merged {len(records)} records into {EVAL_TABLE}")

# COMMAND ----------
# MAGIC %md ## Step 4 — Predict function (streaming for clean traces)

# COMMAND ----------

import json, requests

# Auth: use the notebook context's API token (works in job clusters)
ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
HOST  = ctx.apiUrl().get()
TOKEN = ctx.apiToken().get()
INVOKE_URL = f"{HOST}/serving-endpoints/{ENDPOINT}/invocations"

@mlflow.trace
def predict_fn(question: str) -> str:
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {"input": [{"role": "user", "content": question}], "stream": True}
    final_msgs = []
    with requests.post(INVOKE_URL, headers=headers, json=payload, stream=True, timeout=180) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            try:
                ev = json.loads(line[5:].strip())
            except Exception:
                continue
            if ev.get("type") == "response.output_item.done":
                item = ev.get("item", {})
                if item.get("type") == "message" and item.get("role") == "assistant":
                    for c in item.get("content", []):
                        t = c.get("text", "")
                        if t and not t.startswith("<name>"):
                            final_msgs.append(t)
    return final_msgs[-1] if final_msgs else ""

print(predict_fn("How many projects in Pennsylvania have a Poor or Critical condition rating?")[:200])

# COMMAND ----------
# MAGIC %md ## Step 5 — Scorers
# MAGIC
# MAGIC **Built-in LLM judges:** Correctness, Safety, and a Guidelines-based groundedness check.
# MAGIC **Custom judge:** tool_routing — did the supervisor pick the right tool path?

# COMMAND ----------

from mlflow.genai.scorers import Correctness, Safety, Guidelines, scorer

groundedness = Guidelines(
    name="groundedness",
    guidelines=(
        "The response must cite specific inspection report IDs (e.g., INS-SS-002) "
        "when making factual claims about inspection findings, OR clearly describe "
        "database query results when answering portfolio questions. "
        "Fabricated or unsupported claims should score poorly."
    ),
)

@scorer
def tool_routing(inputs, outputs, expectations):
    """Did the supervisor pick the right tool path?"""
    import re
    expected = expectations.get("expected_tool", "") if expectations else ""
    text     = str(outputs or "")

    has_report_id = bool(re.search(r"INS-[A-Z]{2}-\d{3}", text))
    has_tabular   = bool(re.search(r"\|\s*[-\w]+\s*\|", text) or
                         re.search(r"(?:\d+\s+projects|\$[\d,]+|\baverage\b|\btotal\b)", text.lower()))
    declines      = any(p in text.lower() for p in ["outside", "out of scope", "unable to help", "only answer", "can only", "i'm inspectiq"])

    if expected == "rag":
        return 1.0 if has_report_id else 0.0
    if expected == "sql":
        return 1.0 if (has_tabular and not declines) else 0.0
    if expected == "both":
        if has_report_id and has_tabular:
            return 1.0
        if has_report_id or has_tabular:
            return 0.5
        return 0.0
    if expected == "none":
        return 1.0 if declines else 0.0
    return 0.5

# COMMAND ----------
# MAGIC %md ## Step 6 — Run evaluation on the dataset

# COMMAND ----------

with mlflow.start_run(run_name="supervisor-eval-v1") as run:
    results = mlflow.genai.evaluate(
        data=dataset,
        predict_fn=lambda question: predict_fn(question),
        scorers=[
            Correctness(),
            Safety(),
            groundedness,
            tool_routing,
        ],
    )
    run_id = run.info.run_id
    print(f"\nRun ID:  {run_id}")
    print(f"Run URL: https://e2-demo-field-eng.cloud.databricks.com/ml/experiments/{EXPERIMENT_ID}/runs/{run_id}")

# COMMAND ----------
# MAGIC %md ## Step 7 — Summary

# COMMAND ----------

print("Aggregate scorer metrics:")
metrics = getattr(results, "metrics", {}) or {}
for k, v in sorted(metrics.items()):
    print(f"  {k}: {v}")

print(f"\nDataset: {EVAL_TABLE}")
print(f"Experiment: https://e2-demo-field-eng.cloud.databricks.com/ml/experiments/{EXPERIMENT_ID}")
print(f"Traces tab: https://e2-demo-field-eng.cloud.databricks.com/ml/experiments/{EXPERIMENT_ID}/traces")
