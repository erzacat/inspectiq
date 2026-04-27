# InspectIQ — Michael Baker International

Conversational AI knowledge assistant that turns static infrastructure inspection
reports into searchable, queryable intelligence. Engineers ask questions in plain
English — InspectIQ routes across disciplines (Structural Steel, Concrete, Asphalt),
retrieves the relevant inspection documents, surfaces key findings, and cites
sources.

This package is a snapshot of the live demo running in Databricks Field Eng.
All assets target Unity Catalog `mbi_demo.inspectiq`.

---

## What's included

```
inspectiq-handoff/
├── databricks.yml          DAB root (customize catalog/warehouse via variables)
├── resources/              DAB resource definitions
│   ├── pipeline.yml            DLT pipeline (inspectiq-dlt)
│   ├── job.yml                 One-shot setup job (runs all notebooks in order)
│   ├── app.yml                 Databricks App (inspectiq-mbi)
│   ├── dlt_pipeline_live.json  Reference: live pipeline spec as of export
│   ├── vector_search_endpoint.json
│   ├── vector_search_index.json
│   └── app_live.json
├── notebooks/              All notebooks, flat layout
│   ├── 01_generate_inspection_pdfs.py
│   ├── 02_structured_data.py              (standalone structured data; optional)
│   ├── 02a_generate_source_data.py        (writes raw JSON into source_data volume)
│   ├── 02b_ingest_and_clean.py            (DLT bronze → silver)
│   ├── 02c_build_gold.py                  (DLT gold tables)
│   ├── 02d_create_metric_views.py         (UC metric views)
│   ├── 03_rag_pipeline.py                 (chunk → embed → VS index)
│   ├── 04_document_ingestion_pipeline.py  (alternative ingestion; reference)
│   ├── 04_knowledge_assistant.py          (deploys KA endpoint)
│   ├── 05_supervisor_agent.py             (deploys supervisor endpoint)
│   ├── 07_mlflow_evaluation.py            (eval harness)
│   └── inspectiq_supervisor_model.py      (helper module for supervisor)
├── app/                    Databricks App source (live export of inspectiq-mbi)
├── dashboard/              AI/BI Executive Dashboard definition
│   ├── InspectIQ — Infrastructure Executive Dashboard.lvdash.json
│   └── _api_response.json  (full API metadata, for reference)
├── genie/                  Genie space config (manual setup; see SETUP.md)
│   ├── space_info.json
│   ├── instructions.json
│   └── curated_questions.json
└── endpoints/              Live model serving configs (reference)
    ├── knowledge_assistant.json
    └── supervisor.json
```

## Deploy

1. Read `SETUP.md` end-to-end — there are three manual steps (Genie space,
   endpoint promotion, app environment var) that DABs don't cover cleanly.
2. `databricks bundle validate`
3. `databricks bundle deploy`
4. `databricks bundle run inspectiq_setup` (runs the full pipeline end-to-end)
5. Create the Genie space (see `genie/README.md` or `SETUP.md`)
6. Import the dashboard and point it at the new warehouse
7. Visit the app URL and verify chat works

## Architecture

```
Unity Catalog: mbi_demo.inspectiq
├── Volumes
│   ├── inspection_docs        (PDFs)
│   ├── source_data            (raw JSON feed)
│   ├── policy_standards       (FHWA guidelines, manuals)
│   └── regional_intelligence  (State DOT reports)
├── DLT Pipeline: inspectiq-dlt
│   ├── bronze_inspections → silver_inspections
│   └── gold_{condition_summary, cost_by_discipline, overdue_inspections,
│              priority_queue, state_summary, inspector_workload}
├── Metric Views (UC semantic layer)
│   ├── metrics_asset_portfolio
│   └── metrics_overdue_risk
├── Structured tables
│   ├── project_assets, inspection_findings, corrective_actions, element_conditions
│   └── RBAC views: project_assets_as_{director, national_admin, pa_inspector}
├── Documents
│   ├── doc_chunks → Vector Search index mbi_demo.inspectiq.doc_index
│   │   (endpoint: mbi-inspectiq-vs)
│   └── regional_docs
└── Models / Endpoints
    ├── mbi_demo.inspectiq.inspectiq_agent      → mbi-inspectiq-agent
    └── mbi_demo.inspectiq.inspectiq_supervisor → mbi-inspectiq-supervisor

Databricks App: inspectiq-mbi
├── FastAPI server (app/server) + React/Vite frontend (app/frontend)
└── Calls mbi-inspectiq-supervisor (or built-in router) + embeds Executive Dashboard

Genie Space: InspectIQ Project Intelligence
└── Surfaces the metric views + structured tables
```

See `SETUP.md` for step-by-step deployment and `DEMO_SCRIPT.md` (optional,
add your own) for the demo narrative.
