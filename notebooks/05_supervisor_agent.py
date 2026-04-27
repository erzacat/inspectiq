# Databricks notebook source
# MAGIC %md
# MAGIC # InspectIQ — Phase 5: Supervisor Agent
# MAGIC
# MAGIC The supervisor routes queries intelligently between two tools:
# MAGIC - **`search_inspection_reports`** (RAG) — for document-level questions about findings,
# MAGIC   deficiencies, recommendations, safety risks, specific reports
# MAGIC - **`query_project_database`** (SQL) — for aggregate/analytical questions like
# MAGIC   "how many", "which projects", "total cost", "by state", trends
# MAGIC
# MAGIC The user never specifies which tool — the supervisor decides based on intent.
# MAGIC This endpoint is what the Databricks App calls.
# MAGIC
# MAGIC **UI Alternative — Mosaic AI Agent:** See the "Manual Agent UI" section at the bottom
# MAGIC for step-by-step instructions to build the supervisor via the Databricks UI instead of code.

# COMMAND ----------

# MAGIC %pip install mlflow>=2.16 langchain==0.3.7 langchain-community==0.3.7 \
# MAGIC   databricks-vectorsearch databricks-langchain==0.3.0 pydantic --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import mlflow, time
from mlflow.models.resources import (
    DatabricksServingEndpoint,
    DatabricksVectorSearchIndex,
    DatabricksTable,
    DatabricksSQLWarehouse,
)

catalog        = "mbi_demo"
schema         = "inspectiq"
vs_endpoint    = "mbi-inspectiq-vs"
vs_index       = f"{catalog}.{schema}.doc_index"
asset_table    = f"{catalog}.{schema}.project_assets"
model_name     = f"{catalog}.{schema}.inspectiq_supervisor"
endpoint_name  = "mbi-inspectiq-supervisor"
LLM_MODEL      = "databricks-claude-sonnet-4-5"

mlflow.set_registry_uri("databricks-uc")

# COMMAND ----------
# MAGIC %md ## Step 1 — Define Tools

# COMMAND ----------

# NOTE: Smoke-test at notebook scope is intentionally omitted. The pyfunc class is defined
# below in its own scope. This avoids cloudpickle walking notebook-global state (which
# captures a reference to dbutils via the Spark session and fails serialization).
# Live smoke-testing happens against the deployed endpoint in Step 4.

# COMMAND ----------
# MAGIC %md ## Step 2 — Supervisor Agent System Prompt

# COMMAND ----------

SUPERVISOR_PROMPT = """You are InspectIQ Supervisor, an intelligent infrastructure intelligence assistant for Michael Baker International (MBI).

You have access to two tools:
1. **search_inspection_reports** — searches the full text of 10 MBI inspection PDFs (structural steel, concrete, asphalt)
2. **query_project_database** — queries a structured database of all inspection projects

**Routing logic (decide before calling any tool):**
- Questions about WHAT was found, observed, recommended, or identified → use search_inspection_reports
- Questions about HOW MANY, WHICH PROJECTS, TOTAL COST, BY STATE/TYPE, OVERDUE → use query_project_database
- Questions that combine both (e.g. "tell me about concrete projects with poor ratings") → use query_project_database first for the project list, then search_inspection_reports for detailed findings
- If unsure, try search_inspection_reports first

**Response style:**
- Cite report IDs (e.g. INS-SS-002) for every factual claim from documents
- Be specific and technical — your audience includes licensed PEs, PMs, and executives
- Use bullet points for multi-part answers
- Clearly separate structured data results from document findings
- If no relevant information is found, say so — do not fabricate

**Domain knowledge:**
- Condition ratings: 1–9 (FHWA) — Critical ≤3, Poor ≤5, Fair ≤7, Good 8–9
- PCI (Pavement Condition Index): 0–100 — Poor <40, Fair 40–55, Good 55–70
- Safety-flagged projects require immediate attention
- Disciplines: Structural Steel, Concrete, Asphalt"""

# COMMAND ----------
# MAGIC %md ## Step 3 — Log to UC Registry (code-based model)
# MAGIC
# MAGIC The `InspectIQSupervisor` class lives in `inspectiq_supervisor_model.py` next to this
# MAGIC notebook. Code-based logging avoids cloudpickle walking notebook globals (which
# MAGIC captures a reference to `dbutils` and fails serialization).

# COMMAND ----------

import os, pandas as pd

WAREHOUSE_ID = "4b9b953939869799"  # Shared Unity Catalog Serverless (same warehouse powering the dashboard)

model_config = {
    "vs_endpoint":   vs_endpoint,
    "vs_index":      vs_index,
    "asset_table":   asset_table,
    "warehouse_id":  WAREHOUSE_ID,
    "llm_model":     LLM_MODEL,
    "system_prompt": SUPERVISOR_PROMPT,
}

sample_input = pd.DataFrame({
    "messages": [[{"role": "user", "content": "How many projects have safety flags and what were the issues?"}]]
})

# Resolve model code path (sibling to this notebook in the Workspace)
MODEL_CODE_PATH = "/Workspace/Users/emily.liu@databricks.com/inspectiq-demo2/notebooks/inspectiq_supervisor_model.py"

with mlflow.start_run(run_name="inspectiq-supervisor"):
    mlflow.log_params({"llm_model": LLM_MODEL, "vs_index": vs_index, "tools": "rag+sql"})
    model_info = mlflow.pyfunc.log_model(
        artifact_path        = "inspectiq_supervisor",
        python_model         = MODEL_CODE_PATH,          # code-based logging
        model_config         = model_config,
        input_example        = sample_input,
        registered_model_name= model_name,
        resources=[
            DatabricksServingEndpoint(endpoint_name=LLM_MODEL),
            DatabricksVectorSearchIndex(index_name=vs_index),
            DatabricksTable(table_name=asset_table),
            DatabricksSQLWarehouse(warehouse_id=WAREHOUSE_ID),
        ],
        pip_requirements=[
            "mlflow>=2.16", "langchain==0.3.7", "langchain-community==0.3.7",
            "databricks-vectorsearch", "databricks-langchain==0.3.0", "databricks-sdk",
        ],
    )
    print(f"Model logged: {model_info.model_uri}")

# COMMAND ----------
# MAGIC %md ## Step 4 — Deploy to Model Serving

# COMMAND ----------

import mlflow.deployments

deploy_client = mlflow.deployments.get_deploy_client("databricks")
mlflow_client = mlflow.tracking.MlflowClient()

versions = mlflow_client.search_model_versions(f"name='{model_name}'")
latest   = max(int(v.version) for v in versions)
print(f"Deploying version {latest}")

served_name = f"inspectiq-supervisor-v{latest}"
endpoint_config = {
    "served_entities": [{
        "name":                  served_name,
        "entity_name":           model_name,
        "entity_version":        str(latest),
        "workload_size":         "Small",
        "scale_to_zero_enabled": True,
    }],
    "traffic_config": {
        "routes": [{"served_model_name": served_name, "traffic_percentage": 100}]
    },
}

def _get_or_none(name):
    try:
        return deploy_client.get_endpoint(name)
    except Exception:
        return None

existing = _get_or_none(endpoint_name)
if existing:
    waited = 0
    while existing and existing.get("state", {}).get("config_update") == "IN_PROGRESS" and waited < 30*60:
        print(f"  existing endpoint update IN_PROGRESS, waiting... ({waited}s)")
        time.sleep(30); waited += 30
        existing = _get_or_none(endpoint_name)
    print("Endpoint exists — updating")
    deploy_client.update_endpoint(endpoint=endpoint_name, config=endpoint_config)
else:
    print("Creating endpoint")
    deploy_client.create_endpoint(name=endpoint_name, config=endpoint_config)

print("Waiting for READY...")
for _ in range(60):
    ep = deploy_client.get_endpoint(endpoint_name)
    ready  = ep.get("state", {}).get("ready", "?")
    update = ep.get("state", {}).get("config_update", "?")
    print(f"  ready={ready} update={update}")
    if ready == "READY":
        break
    if update == "UPDATE_FAILED":
        raise RuntimeError(f"Endpoint deployment failed. State: {ep.get('state')}. Check service logs.")
    time.sleep(30)

print(f"\nPhase 5 complete. Supervisor endpoint: {endpoint_name}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Manual Agent UI — Mosaic AI Agent Builder (Alternative)
# MAGIC
# MAGIC If you prefer to configure the supervisor agent via the Databricks UI instead of code:
# MAGIC
# MAGIC ### Option A: AI Playground → Convert to Agent
# MAGIC 1. Databricks sidebar → **Playground**
# MAGIC 2. Select model: `databricks-claude-sonnet-4-5`
# MAGIC 3. In System Prompt, paste the SUPERVISOR_PROMPT from this notebook
# MAGIC 4. Click **Add Tool** → Select **Vector Search**
# MAGIC    - Endpoint: `mbi-inspectiq-vs`
# MAGIC    - Index: `mbi_demo.inspectiq.doc_index`
# MAGIC    - Columns to return: `chunk_id, doc_id, discipline, content`
# MAGIC    - Tool description: "Search MBI inspection reports for findings, deficiencies, recommendations"
# MAGIC 5. Click **Add Tool** → Select **Unity Catalog Function** (if you registered query_project_database as a UC function)
# MAGIC    - Or use **SQL Warehouse** tool pointed at `mbi_demo.inspectiq.project_assets`
# MAGIC 6. Test with sample questions, then click **Export as Agent**
# MAGIC 7. Register the agent and deploy to serving endpoint `mbi-inspectiq-supervisor`
# MAGIC
# MAGIC ### Option B: Mosaic AI Agent Framework UI
# MAGIC 1. Databricks sidebar → **Machine Learning** → **AI Agents** → **Create Agent**
# MAGIC 2. Name: `InspectIQ Supervisor`
# MAGIC 3. Model: `databricks-claude-sonnet-4-5`
# MAGIC 4. System Prompt: paste SUPERVISOR_PROMPT
# MAGIC 5. Tools:
# MAGIC    - Vector Search: `mbi_demo.inspectiq.doc_index` (6 results)
# MAGIC    - SQL: enable and point to `mbi_demo.inspectiq.project_assets`
# MAGIC 6. Deploy → copy endpoint URL for the app
