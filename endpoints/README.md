# Model Serving Endpoints

Two endpoints power InspectIQ:

| Endpoint | UC Model | Purpose | Created by |
|---|---|---|---|
| `mbi-inspectiq-agent` | `mbi_demo.inspectiq.inspectiq_agent` | Knowledge Assistant (RAG over inspection PDFs) | `notebooks/04_knowledge_assistant.py` |
| `mbi-inspectiq-supervisor` | `mbi_demo.inspectiq.inspectiq_supervisor` | Router: dispatches to Genie or Knowledge Assistant | `notebooks/05_supervisor_agent.py` |

## Live configs (reference)

`knowledge_assistant.json` and `supervisor.json` capture the live configuration
as exported from the source workspace:
- Workload: Small, CPU, scale-to-zero enabled
- Single served entity, 100% traffic

## How they get created

The endpoints aren't defined as DAB resources because they depend on UC models
that get registered **inside** the notebooks. The setup job runs both notebooks
in order, which:
1. Registers the MLflow/ChatAgent model to Unity Catalog
2. Calls `agents.deploy(...)` or equivalent to promote a model version to a
   model serving endpoint

If you need to recreate an endpoint manually:

```bash
# Deploy a specific model version (endpoint name will be created/updated)
databricks serving-endpoints create --json '{
  "name": "mbi-inspectiq-supervisor",
  "config": {
    "served_entities": [
      {
        "name": "inspectiq-supervisor-v1",
        "entity_name": "mbi_demo.inspectiq.inspectiq_supervisor",
        "entity_version": "1",
        "workload_size": "Small",
        "workload_type": "CPU",
        "scale_to_zero_enabled": true
      }
    ],
    "traffic_config": {
      "routes": [
        {"served_model_name": "inspectiq-supervisor-v1", "traffic_percentage": 100}
      ]
    }
  }
}'
```

## Validation

```bash
databricks serving-endpoints query mbi-inspectiq-agent \
  --json '{"messages":[{"role":"user","content":"What are the most common defects found in bridge inspections?"}]}'

databricks serving-endpoints query mbi-inspectiq-supervisor \
  --json '{"messages":[{"role":"user","content":"Which assets are overdue and safety-flagged?"}]}'
```

Both should return an assistant message. Supervisor may take longer on first
query while scaling from zero.
