# Genie Space Setup — InspectIQ Project Intelligence

Genie spaces don't yet have a clean DAB / API-based create flow that preserves
curated questions + instructions + column hints, so this step is manual. All
the content you need is captured in this directory.

## Files

- `space_info.json` — space metadata (title, description, tables, warehouse)
- `instructions.json` — 22 SQL hints to paste into the Instructions panel
- `curated_questions.json` — 25 question/answer pairs for the Sample Queries panel

## Create the space

1. In the workspace: **Genie → Create new space**
2. **Title:** `InspectIQ Project Intelligence`
3. **Description:** copy from `space_info.json` → `description`
4. **Warehouse:** the one in `databricks.yml` `warehouse_id`
5. **Tables** (from `space_info.json` → `table_identifiers`):
   - `mbi_demo.inspectiq.project_assets`
   - `mbi_demo.inspectiq.inspection_findings`
   - `mbi_demo.inspectiq.corrective_actions`
   - `mbi_demo.inspectiq.element_conditions`
   - `mbi_demo.inspectiq.metrics_asset_portfolio`  ← metric view
   - `mbi_demo.inspectiq.metrics_overdue_risk`     ← metric view

## Populate instructions

Open `instructions.json`. For each entry, click **Add instruction** in Genie:
- **Title:** `title` field
- **SQL:** `content` field

## Populate sample queries

Open `curated_questions.json`. For each entry, click **Add sample query**:
- **Question:** `question_text`
- **SQL:** `answer_text`

## Validation

Ask these three questions in the space after setup:
1. "Which assets are both overdue and safety-flagged, ranked by how late they are?"
2. "What's our overdue percentage by state?"
3. "Top 10 repair costs this year."

All three should return rows. If they don't, the tables or metric views aren't
populated — re-run the setup job.

## Why the metric views matter

`metrics_asset_portfolio` and `metrics_overdue_risk` are UC MetricViews — they
give Genie governed measures (overdue_pct, safety_flagged_pct, nbis_deficient_count,
avg_days_overdue, total_overdue_cost) with synonyms baked in. Without them, Genie
has to compute aggregates from raw tables and accuracy drops noticeably on
percentage/rate questions.
