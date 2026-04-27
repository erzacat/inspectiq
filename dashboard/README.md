# AI/BI Executive Dashboard

File: `InspectIQ — Infrastructure Executive Dashboard.lvdash.json`

## Source

Exported from the live workspace dashboard (ID `01f13232608316f4b4411a791afe86c4`)
via the Lakeview API. `_api_response.json` has the raw API metadata
(warehouse ID, timestamps, etc.) for reference.

## Import

1. In the workspace: **Dashboards → Import dashboard**
2. Upload `InspectIQ — Infrastructure Executive Dashboard.lvdash.json`
3. Assign a SQL warehouse
4. Publish

## App integration

The app embeds this dashboard by ID in:

```tsx
// app/frontend/src/components/EmbeddedDashboardView.tsx
const DASHBOARD_ID = '01f13232608316f4b4411a791afe86c4'
```

After importing the dashboard into a new workspace, update `DASHBOARD_ID`
to the new ID (shown in the dashboard URL), then rebuild and redeploy the app:

```bash
cd app/frontend && npm install && npm run build
databricks bundle deploy -t dev
```

## Datasets

The dashboard queries:
- `<catalog>.<schema>.project_assets` — asset-level portfolio
- `<catalog>.<schema>.gold_*` — aggregate materialized views
- `<catalog>.<schema>.metrics_asset_portfolio` — metric view

All populated by the DLT pipeline (`resources/pipeline.yml`) plus
`02d_create_metric_views`.
