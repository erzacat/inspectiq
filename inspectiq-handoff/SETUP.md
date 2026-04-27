# InspectIQ Setup Guide

End-to-end instructions for standing up the InspectIQ demo in a Databricks
workspace using this bundle.

**Target state** (what "done" looks like):
- Unity Catalog schema `<catalog>.inspectiq` populated with bronze/silver/gold
  tables, metric views, RBAC views, and a Vector Search index.
- Two model serving endpoints: `mbi-inspectiq-agent` (Knowledge Assistant)
  and `mbi-inspectiq-supervisor` (router).
- AI/BI dashboard `InspectIQ — Infrastructure Executive Dashboard`.
- Genie space `InspectIQ Project Intelligence`.
- Databricks App `inspectiq-mbi` serving the demo UI.

---

## 0. Prerequisites

- Databricks CLI ≥ v0.240 with authenticated profile
- Workspace with: Unity Catalog, Vector Search, Model Serving, Databricks Apps, AI/BI
- Permissions to create catalog, schema, volumes, pipelines, apps, endpoints
- A SQL warehouse the bundle can reuse (put its ID in `databricks.yml` `warehouse_id`)

Edit `databricks.yml` to match your target:
```yaml
variables:
  catalog:
    default: mbi_demo              # ← change if you use a different catalog
  schema:
    default: inspectiq
  warehouse_id:
    default: 4b9b953939869799       # ← put your warehouse ID here
  vector_search_endpoint:
    default: mbi-inspectiq-vs       # ← endpoint will be created if it doesn't exist
```

---

## 1. Deploy the bundle

```bash
databricks bundle validate
databricks bundle deploy -t dev
```

This uploads notebooks, the DLT pipeline, the job, and the app source to the
workspace. Nothing runs yet.

---

## 2. Run the setup job

```bash
databricks bundle run inspectiq_setup -t dev
```

Runs end-to-end, in order:

1. `01_generate_inspection_pdfs` — Synthetic PDFs into
   `<catalog>.<schema>.inspection_docs` UC volume (~2 min)
2. `02a_generate_source_data` — Raw JSON into `source_data` volume (~1 min)
3. **DLT pipeline `inspectiq-dlt`** — bronze → silver → gold (~10 min first run)
4. `02d_create_metric_views` — Creates `metrics_asset_portfolio` and
   `metrics_overdue_risk` UC metric views
5. `03_rag_pipeline` — Chunks PDFs, builds embeddings, creates Vector Search
   endpoint `mbi-inspectiq-vs` and index `<catalog>.<schema>.doc_index` (~25 min)
6. `04_knowledge_assistant` — Logs the RAG agent to UC, deploys endpoint
   `mbi-inspectiq-agent` (~10 min)
7. `05_supervisor_agent` — Logs the supervisor, deploys endpoint
   `mbi-inspectiq-supervisor` (~10 min)

Optional follow-up: `07_mlflow_evaluation` (not wired into the job) for agent eval.

---

## 3. Manual step — Genie space

See `genie/README.md` for full detail. Summary:

1. In the workspace UI: **Genie → New space**
2. **Warehouse:** same as `${var.warehouse_id}`
3. **Tables:** add these six (order doesn't matter):
   - `<catalog>.<schema>.project_assets`
   - `<catalog>.<schema>.inspection_findings`
   - `<catalog>.<schema>.corrective_actions`
   - `<catalog>.<schema>.element_conditions`
   - `<catalog>.<schema>.metrics_asset_portfolio`  ← metric view
   - `<catalog>.<schema>.metrics_overdue_risk`     ← metric view
4. **Description:** copy from `genie/space_info.json` field `description`.
5. **Sample questions (curated):** 25 captured in
   `genie/curated_questions.json` — paste each `question_text` / `answer_text`
   pair into the Genie "Sample queries" panel.
6. **Instructions:** 22 SQL hints in `genie/instructions.json` — paste into the
   Genie "Instructions" panel.

---

## 4. Manual step — AI/BI Executive Dashboard

1. In the workspace UI: **Dashboards → Import dashboard**
2. Upload `dashboard/InspectIQ — Infrastructure Executive Dashboard.lvdash.json`
3. Set the default warehouse to `${var.warehouse_id}`
4. Publish the dashboard
5. Copy its dashboard ID from the URL (format: `…/dashboardsv3/<ID>/…`)
6. Update the app to embed the new ID:
   - Edit `app/frontend/src/components/EmbeddedDashboardView.tsx`
   - Replace `DASHBOARD_ID = '01f13232608316f4b4411a791afe86c4'` with your new ID
   - Rebuild: `cd app/frontend && npm install && npm run build`
   - Redeploy: `databricks bundle deploy -t dev`

---

## 5. Manual step — App environment vars

The live app references two external values that need updating:

```yaml
# app/app.yaml
env:
  - name: AGENT_ENDPOINT
    value: "https://<YOUR-WORKSPACE>.cloud.databricks.com/serving-endpoints/mbi-inspectiq-supervisor/invocations"
  - name: USE_SUPERVISOR
    value: "false"   # flip to "true" after step 3 validates the endpoint
  - name: MLFLOW_EXPERIMENT_ID
    value: "<your experiment id>"   # create a new MLflow experiment, paste its ID
  - name: MLFLOW_TRACKING_URI
    value: "databricks"
```

Redeploy the bundle after editing: `databricks bundle deploy -t dev`.

---

## 6. Validation

1. **App smoke test** — open the app URL, ask:
   - "What are our most overdue bridge inspections?"
   - "Summarize recent findings for PA assets."
   - "What repairs are recommended for asset ASSET-0042?"
2. **Genie smoke test** — open the space, run 2-3 of the curated questions
3. **Dashboard smoke test** — confirm the embedded dashboard loads in the app
4. **Endpoint smoke test:**
   ```bash
   databricks serving-endpoints query mbi-inspectiq-supervisor --json '{"messages":[{"role":"user","content":"Which assets are overdue?"}]}'
   ```

---

## Cleanup (optional)

```bash
databricks bundle destroy -t dev
```

Destroys pipeline, job, and app. Does **not** drop the catalog, endpoints, or
Vector Search index — remove those manually if needed:
```bash
databricks serving-endpoints delete mbi-inspectiq-supervisor
databricks serving-endpoints delete mbi-inspectiq-agent
databricks vector-search-indexes delete-index <catalog>.<schema>.doc_index
databricks vector-search-endpoints delete-endpoint mbi-inspectiq-vs
# then drop the catalog from the UI or via SQL
```
