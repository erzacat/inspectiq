# Databricks notebook source
# MAGIC %md
# MAGIC # InspectIQ — Phase 4: Knowledge Assistant Agent
# MAGIC
# MAGIC Builds and deploys the **InspectIQ RAG agent** to a Model Serving endpoint.
# MAGIC - Tool: Vector Search retriever over all 10 inspection PDFs
# MAGIC - LLM: databricks-claude-sonnet-4-5
# MAGIC - Key behavior: user does NOT specify which document — the agent finds the right one
# MAGIC - Cites report IDs (e.g. INS-SS-002) for every factual claim

# COMMAND ----------

# MAGIC %pip install mlflow>=2.16 langchain==0.3.7 langchain-community==0.3.7 \
# MAGIC   databricks-vectorsearch databricks-langchain==0.3.0 pydantic --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import mlflow, time
from databricks.vector_search.client import VectorSearchClient
from mlflow.models.resources import DatabricksServingEndpoint, DatabricksVectorSearchIndex

catalog      = "mbi_demo"
schema       = "inspectiq"
vs_endpoint  = "mbi-inspectiq-vs"
vs_index     = f"{catalog}.{schema}.doc_index"
model_name   = f"{catalog}.{schema}.inspectiq_agent"
endpoint_name = "mbi-inspectiq-agent"
LLM_MODEL    = "databricks-claude-sonnet-4-5"

mlflow.set_registry_uri("databricks-uc")

# COMMAND ----------
# MAGIC %md ## Step 1 — Build and Smoke-Test Agent

# COMMAND ----------

from databricks_langchain import ChatDatabricks, DatabricksVectorSearch
from langchain.tools.retriever import create_retriever_tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

vs_retriever = DatabricksVectorSearch(
    endpoint   = vs_endpoint,
    index_name = vs_index,
    columns    = ["chunk_id", "doc_id", "discipline", "content"],
).as_retriever(search_kwargs={"k": 6})

retriever_tool = create_retriever_tool(
    retriever   = vs_retriever,
    name        = "search_inspection_reports",
    description = (
        "Search Michael Baker International inspection reports across structural steel, "
        "concrete, and asphalt disciplines. "
        "Use this tool for ANY question about inspection findings, deficiencies, safety risks, "
        "corrective actions, recommendations, condition ratings, or engineering observations. "
        "You do NOT need to know which specific report to search — the tool finds the most "
        "relevant documents automatically. "
        "Input: a plain-language question or keyword phrase."
    ),
)

SYSTEM_PROMPT = """You are InspectIQ, an intelligent inspection intelligence assistant for Michael Baker International (MBI).

MBI engineers, project managers, and executives use you to find answers from the firm's inspection reports — structural steel, concrete, and asphalt/pavement assessments.

**How you respond:**
- ALWAYS use the search_inspection_reports tool before answering. Do not rely on prior knowledge.
- Cite your source report for every factual claim: include the Report ID (e.g. INS-SS-002, INS-CO-001) in parentheses.
- Be specific and technical. Your audience includes licensed PEs and field inspectors.
- If a question spans multiple reports, search multiple times with different keywords and synthesize.
- If you cannot find a direct answer in the documents, say so clearly rather than guessing.
- For safety-critical findings, call them out prominently.
- Use bullet points or numbered lists for multi-part answers.
- Keep answers concise but complete — no fluff, no repetition.

**Report disciplines:**
- Structural Steel: steel frame buildings, parking garages, overpasses, industrial structures
- Concrete: bridge decks, retaining walls, parking structures
- Asphalt: airport runways, highways, industrial roads, streetscapes

**Key facts to know:**
- Condition ratings: 1–9 scale (FHWA) — Critical ≤3, Poor ≤5, Fair ≤7, Good 8–9
- PCI (Pavement Condition Index): 0–100 — Failed <25, Poor 25–40, Fair 40–55, Good 55–70, Very Good >70
- Report ID format: INS-SS-### (steel), INS-CO-### (concrete), INS-AP-### (asphalt)"""

llm = ChatDatabricks(endpoint=LLM_MODEL, temperature=0.1, max_tokens=2048)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

agent    = create_tool_calling_agent(llm=llm, tools=[retriever_tool], prompt=prompt)
executor = AgentExecutor(
    agent=agent, tools=[retriever_tool],
    verbose=True, max_iterations=6, handle_parsing_errors=True,
)

# Smoke tests
SMOKE_TESTS = [
    "Were any immediate safety risks identified in the parking garage inspections?",
    "What causes concrete deterioration in these inspection reports and what's recommended?",
    "Which asphalt projects have alligator cracking and what corrective actions were recommended?",
]

for q in SMOKE_TESTS:
    print(f"\n{'='*60}\nQ: {q}")
    result = executor.invoke({"input": q, "chat_history": []})
    print(f"A: {result['output'][:600]}...")

# COMMAND ----------
# MAGIC %md ## Step 2 — Log to UC Model Registry

# COMMAND ----------

import pandas as pd

class InspectIQAgent(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        from databricks_langchain import ChatDatabricks, DatabricksVectorSearch
        from langchain.tools.retriever import create_retriever_tool
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        cfg = context.model_config
        _vs = DatabricksVectorSearch(
            endpoint   = cfg["vs_endpoint"],
            index_name = cfg["vs_index"],
            columns    = ["chunk_id", "doc_id", "discipline", "content"],
        ).as_retriever(search_kwargs={"k": 6})

        _tool = create_retriever_tool(
            retriever   = _vs,
            name        = "search_inspection_reports",
            description = (
                "Search MBI inspection reports across structural steel, concrete, and asphalt. "
                "Finds relevant documents automatically — no need to specify which report."
            ),
        )
        _llm  = ChatDatabricks(endpoint=cfg["llm_model"], temperature=0.1, max_tokens=2048)
        _prompt = ChatPromptTemplate.from_messages([
            ("system", cfg["system_prompt"]),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])
        _agent = create_tool_calling_agent(llm=_llm, tools=[_tool], prompt=_prompt)
        self.executor = AgentExecutor(
            agent=_agent, tools=[_tool], verbose=False,
            max_iterations=6, handle_parsing_errors=True,
        )

    def predict(self, context, model_input, params=None):
        if isinstance(model_input, pd.DataFrame):
            rows = model_input.to_dict(orient="records")
        else:
            rows = [model_input]

        results = []
        for row in rows:
            msgs = row.get("messages", [])
            history, user_msg = [], ""
            for m in msgs:
                if m["role"] == "user":
                    user_msg = m["content"]
                elif m["role"] == "assistant":
                    history.append(("assistant", m["content"]))
            out = self.executor.invoke({"input": user_msg, "chat_history": history})
            results.append(out["output"])
        return results


model_config = {
    "vs_endpoint":   vs_endpoint,
    "vs_index":      vs_index,
    "llm_model":     LLM_MODEL,
    "system_prompt": SYSTEM_PROMPT,
}

sample_input = pd.DataFrame({
    "messages": [[{"role": "user", "content": "Were any safety risks identified in the structural steel inspections?"}]]
})

with mlflow.start_run(run_name="inspectiq-knowledge-assistant"):
    mlflow.log_params({"llm_model": LLM_MODEL, "vs_index": vs_index, "k": 6})
    model_info = mlflow.pyfunc.log_model(
        artifact_path        = "inspectiq_agent",
        python_model         = InspectIQAgent(),
        model_config         = model_config,
        input_example        = sample_input,
        registered_model_name= model_name,
        resources=[
            DatabricksServingEndpoint(endpoint_name=LLM_MODEL),
            DatabricksVectorSearchIndex(index_name=vs_index),
        ],
        pip_requirements=[
            "mlflow>=2.16",
            "langchain==0.3.7",
            "langchain-community==0.3.7",
            "databricks-vectorsearch",
            "databricks-langchain==0.3.0",
        ],
    )
    print(f"Model logged: {model_info.model_uri}")

# COMMAND ----------
# MAGIC %md ## Step 3 — Deploy to Model Serving

# COMMAND ----------

import mlflow.deployments

deploy_client = mlflow.deployments.get_deploy_client("databricks")
mlflow_client = mlflow.tracking.MlflowClient()

versions = mlflow_client.search_model_versions(f"name='{model_name}'")
latest   = max(int(v.version) for v in versions)
print(f"Deploying version {latest}")

served_name = f"inspectiq-agent-v{latest}"
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
    # Wait for any in-flight config update to settle before we touch it
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

print("Waiting for endpoint READY...")
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

# Live test
print("\n=== Live Test ===")
result = deploy_client.predict(
    endpoint = endpoint_name,
    inputs   = {"dataframe_records": [{"messages": [
        {"role": "user", "content": "Were any immediate safety risks identified in the parking garage inspections?"}
    ]}]}
)
print(result["predictions"][0][:600])
print(f"\nPhase 4 complete. Endpoint: {endpoint_name}")
