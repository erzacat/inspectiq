import os
from fastapi import APIRouter, Query
from server.config import get_token, get_workspace_host, WAREHOUSE_ID
import httpx

router = APIRouter()

CATALOG = "mbi_demo"
SCHEMA  = "inspectiq"
TABLE   = f"{CATALOG}.{SCHEMA}.project_assets"
LLM_ENDPOINT = os.environ.get("LLM_ENDPOINT", "databricks-claude-sonnet-4-5")


async def run_query(sql: str) -> list[dict]:
    host, token = get_workspace_host(), get_token()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{host}/api/2.0/sql/statements",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"statement": sql, "warehouse_id": WAREHOUSE_ID,
                  "wait_timeout": "50s", "on_wait_timeout": "CANCEL",
                  "disposition": "INLINE", "format": "JSON_ARRAY"},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"SQL HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    if data.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError(f"SQL failed: {data.get('status',{})}")
    cols  = [c["name"] for c in data.get("manifest", {}).get("schema", {}).get("columns", [])]
    rows  = data.get("result", {}).get("data_array", []) or []
    return [dict(zip(cols, row)) for row in rows]


def _cast_row(row: dict) -> dict:
    """Normalize types for JSON serialisation."""
    for k, v in row.items():
        if isinstance(v, str):
            if v.lower() == "true":  row[k] = True
            elif v.lower() == "false": row[k] = False
            else:
                try: row[k] = int(v)
                except ValueError:
                    try: row[k] = float(v)
                    except ValueError: pass
    return row


REGION_STATES: dict[str, tuple[str, ...]] = {
    "Northeast":   ("NY", "MA", "CT"),
    "Mid-Atlantic": ("PA", "NJ", "DE", "MD"),
    "Southeast":   ("VA", "NC", "GA", "FL"),
    "Midwest":     ("OH", "IL", "MI"),
    "Southwest":   ("TX", "CO"),
    "Pacific":     ("CA", "WA"),
}


def _sql_lit(v: str) -> str:
    """Quote a string literal for SQL, escaping single quotes."""
    return "'" + v.replace("'", "''") + "'"


def build_where(
    region: str = "",
    discipline: str = "",
    condition: str = "",
    client: str = "",
    extra: str = "",
) -> str:
    """Compose a WHERE clause from dashboard filter params. Returns empty string when no filters."""
    filters: list[str] = []
    if region:
        if region in REGION_STATES:
            states = "', '".join(REGION_STATES[region])
            filters.append(f"state IN ('{states}')")
        else:
            filters.append(f"state = {_sql_lit(region)}")
    if discipline:
        filters.append(f"inspection_type = {_sql_lit(discipline)}")
    if condition:
        filters.append(f"condition_category = {_sql_lit(condition)}")
    if client:
        filters.append(f"client = {_sql_lit(client)}")
    if extra:
        filters.append(f"({extra})")
    return f"WHERE {' AND '.join(filters)}" if filters else ""


# ---------------------------------------------------------------------------
# Filter dimension values — powers the dropdowns in the Exec Dashboard filter bar
# ---------------------------------------------------------------------------

@router.get("/assets/filters")
async def get_filter_options():
    rows = await run_query(f"""
        SELECT DISTINCT inspection_type, condition_category, client, state
        FROM {TABLE}
    """)
    regions = sorted({
        next((r for r, states in REGION_STATES.items() if (row.get("state") or "") in states), "Other")
        for row in rows
    })
    disciplines = sorted({r["inspection_type"] for r in rows if r.get("inspection_type")})
    conditions  = ["Critical", "Poor", "Fair", "Good"]
    clients     = sorted({r["client"] for r in rows if r.get("client")})
    return {
        "regions":     regions,
        "disciplines": disciplines,
        "conditions":  conditions,
        "clients":     clients,
    }


# ---------------------------------------------------------------------------
# Portfolio summary — filtered KPIs for the top strip
# ---------------------------------------------------------------------------

@router.get("/assets/summary")
async def get_summary(
    region: str = "", discipline: str = "", condition: str = "", client: str = "",
):
    where = build_where(region, discipline, condition, client)
    rows = await run_query(f"""
        SELECT
            COUNT(*)                                                        AS total_assets,
            SUM(CASE WHEN condition_category = 'Critical' THEN 1 ELSE 0 END) AS critical_count,
            SUM(CASE WHEN condition_category = 'Poor'     THEN 1 ELSE 0 END) AS poor_count,
            SUM(CASE WHEN condition_category = 'Fair'     THEN 1 ELSE 0 END) AS fair_count,
            SUM(CASE WHEN condition_category = 'Good'     THEN 1 ELSE 0 END) AS good_count,
            SUM(CASE WHEN overdue = true      THEN 1 ELSE 0 END)             AS overdue_count,
            ROUND(SUM(estimated_repair_cost), 0)                             AS total_backlog
        FROM {TABLE}
        {where}
    """)
    return _cast_row(rows[0]) if rows else {}


@router.get("/assets/by-region")
async def get_by_region(
    region: str = "", discipline: str = "", condition: str = "", client: str = "",
):
    where = build_where(region, discipline, condition, client)
    rows = await run_query(f"""
        SELECT
            CASE state
                WHEN 'PA' THEN 'Mid-Atlantic'  WHEN 'NJ' THEN 'Mid-Atlantic'
                WHEN 'NY' THEN 'Northeast'     WHEN 'MA' THEN 'Northeast'
                WHEN 'CT' THEN 'Northeast'     WHEN 'DE' THEN 'Mid-Atlantic'
                WHEN 'MD' THEN 'Mid-Atlantic'  WHEN 'VA' THEN 'Southeast'
                WHEN 'NC' THEN 'Southeast'     WHEN 'GA' THEN 'Southeast'
                WHEN 'FL' THEN 'Southeast'     WHEN 'OH' THEN 'Midwest'
                WHEN 'IL' THEN 'Midwest'       WHEN 'MI' THEN 'Midwest'
                WHEN 'TX' THEN 'Southwest'     WHEN 'CO' THEN 'Southwest'
                WHEN 'CA' THEN 'Pacific'       WHEN 'WA' THEN 'Pacific'
                ELSE 'Other'
            END                                              AS region,
            condition_category,
            COUNT(*)                                         AS count,
            ROUND(AVG(condition_rating), 2)                  AS avg_rating,
            ROUND(SUM(estimated_repair_cost), 0)             AS total_cost
        FROM {TABLE}
        {where}
        GROUP BY region, condition_category
        ORDER BY region, condition_category
    """)
    return [_cast_row(r) for r in rows]


@router.get("/assets/top-risk")
async def get_top_risk(
    limit: int = Query(10, ge=1, le=50),
    region: str = "", discipline: str = "", condition: str = "", client: str = "",
):
    where = build_where(region, discipline, condition, client)
    rows = await run_query(f"""
        SELECT
            report_id                  AS asset_id,
            project_name               AS asset_name,
            inspection_type            AS asset_type,
            state                      AS region,
            state,
            condition_rating,
            condition_category,
            overdue                    AS inspection_overdue,
            inspector                  AS lead_inspector,
            estimated_repair_cost      AS estimated_maintenance_cost,
            inspection_date            AS last_inspection_date,
            next_inspection_date       AS next_scheduled_inspection
        FROM {TABLE}
        {where}
        ORDER BY priority_score DESC, condition_rating ASC
        LIMIT {limit}
    """)
    return [_cast_row(r) for r in rows]


@router.get("/assets/by-discipline")
async def get_by_discipline(
    region: str = "", discipline: str = "", condition: str = "", client: str = "",
):
    where = build_where(region, discipline, condition, client)
    rows = await run_query(f"""
        SELECT
            inspection_type,
            condition_category,
            COUNT(*)                             AS count,
            ROUND(AVG(condition_rating), 2)      AS avg_rating,
            ROUND(SUM(estimated_repair_cost), 0) AS total_cost
        FROM {TABLE}
        {where}
        GROUP BY inspection_type, condition_category
        ORDER BY inspection_type, condition_category
    """)
    return [_cast_row(r) for r in rows]


# ---------------------------------------------------------------------------
# Compliance & backlog risk — overdue, NBIS deficient, safety flags, days overdue
# ---------------------------------------------------------------------------

@router.get("/assets/compliance")
async def get_compliance(
    region: str = "", discipline: str = "", condition: str = "", client: str = "",
):
    where = build_where(region, discipline, condition, client)
    rows = await run_query(f"""
        SELECT
            COUNT(*)                                                         AS total_assets,
            SUM(CASE WHEN overdue        = true THEN 1 ELSE 0 END)            AS overdue_count,
            SUM(CASE WHEN safety_flagged = true THEN 1 ELSE 0 END)            AS safety_flagged_count,
            SUM(CASE WHEN nbis_deficient = true THEN 1 ELSE 0 END)            AS nbis_deficient_count,
            SUM(CASE WHEN overdue = true AND safety_flagged = true THEN 1 ELSE 0 END) AS overdue_and_safety,
            COALESCE(ROUND(AVG(CASE WHEN overdue = true THEN days_overdue END), 0), 0) AS avg_days_overdue,
            COALESCE(MAX(CASE WHEN overdue = true THEN days_overdue END), 0)  AS max_days_overdue,
            ROUND(SUM(CASE WHEN overdue = true THEN estimated_repair_cost ELSE 0 END), 0) AS overdue_cost_exposure
        FROM {TABLE}
        {where}
    """)
    buckets = await run_query(f"""
        SELECT
            CASE
                WHEN days_overdue IS NULL OR days_overdue <= 0 THEN 'On schedule'
                WHEN days_overdue <= 30   THEN '1–30 days'
                WHEN days_overdue <= 90   THEN '31–90 days'
                WHEN days_overdue <= 180  THEN '91–180 days'
                ELSE '180+ days'
            END  AS bucket,
            COUNT(*) AS count
        FROM {TABLE}
        {where}
        GROUP BY bucket
    """)
    order = ["On schedule", "1–30 days", "31–90 days", "91–180 days", "180+ days"]
    bucket_map = {r["bucket"]: r["count"] for r in buckets}
    buckets_ordered = [{"bucket": b, "count": int(bucket_map.get(b, 0) or 0)} for b in order]
    return {
        **(_cast_row(rows[0]) if rows else {}),
        "days_overdue_buckets": buckets_ordered,
    }


# ---------------------------------------------------------------------------
# Condition rating trend — inspection_date bucketed by month × condition_category
# ---------------------------------------------------------------------------

@router.get("/assets/trend")
async def get_trend(
    region: str = "", discipline: str = "", condition: str = "", client: str = "",
):
    where = build_where(region, discipline, condition, client)
    rows = await run_query(f"""
        SELECT
            DATE_FORMAT(inspection_date, 'yyyy-MM')           AS month,
            condition_category,
            COUNT(*)                                          AS count,
            ROUND(AVG(condition_rating), 2)                   AS avg_rating
        FROM {TABLE}
        {where}
        GROUP BY month, condition_category
        ORDER BY month
    """)
    return [_cast_row(r) for r in rows]


# ---------------------------------------------------------------------------
# AI-generated narrative exec summary — Foundation Model API call
# ---------------------------------------------------------------------------

@router.get("/assets/narrative")
async def get_narrative(
    region: str = "", discipline: str = "", condition: str = "", client: str = "",
):
    # Build a compact snapshot of the filtered portfolio to feed the LLM.
    summary = await get_summary(region, discipline, condition, client)
    compliance = await get_compliance(region, discipline, condition, client)
    by_region = await get_by_region(region, discipline, condition, client)

    if not summary or not summary.get("total_assets"):
        return {"narrative": "No assets match the selected filters. Adjust the filter bar to see a summary."}

    # Top 3 regions by asset count for narrative color
    region_rollup: dict[str, int] = {}
    for r in by_region:
        region_rollup[r["region"]] = region_rollup.get(r["region"], 0) + int(r.get("count") or 0)
    top_regions = sorted(region_rollup.items(), key=lambda x: -x[1])[:3]

    scope_bits = [b for b in [
        f"region={region}" if region else None,
        f"discipline={discipline}" if discipline else None,
        f"condition={condition}" if condition else None,
        f"client={client}" if client else None,
    ] if b]
    scope = ", ".join(scope_bits) if scope_bits else "entire portfolio"

    facts = {
        "scope":                   scope,
        "total_assets":            summary.get("total_assets", 0),
        "critical_count":          summary.get("critical_count", 0),
        "poor_count":              summary.get("poor_count", 0),
        "good_count":              summary.get("good_count", 0),
        "overdue_count":           summary.get("overdue_count", 0),
        "total_backlog_usd":       summary.get("total_backlog", 0),
        "safety_flagged_count":    compliance.get("safety_flagged_count", 0),
        "nbis_deficient_count":    compliance.get("nbis_deficient_count", 0),
        "overdue_and_safety":      compliance.get("overdue_and_safety", 0),
        "avg_days_overdue":        compliance.get("avg_days_overdue", 0),
        "overdue_cost_exposure":   compliance.get("overdue_cost_exposure", 0),
        "top_regions_by_count":    top_regions,
    }

    system_prompt = (
        "You are the Chief Engineer briefing an executive audience at Michael Baker International. "
        "Given a JSON snapshot of the inspection portfolio, write a concise 3-sentence executive summary. "
        "Sentence 1: the portfolio's overall health in plain language. "
        "Sentence 2: the single most important risk or compliance concern (overdue + safety-flagged "
        "is the highest-urgency combination; call out dollar exposure for backlog). "
        "Sentence 3: the recommended next action for engineering leadership. "
        "Use specific numbers. No markdown, no bullets, no preamble."
    )

    host, token = get_workspace_host(), get_token()
    try:
        async with httpx.AsyncClient(timeout=30) as client_http:
            resp = await client_http.post(
                f"{host}/serving-endpoints/{LLM_ENDPOINT}/invocations",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": f"Portfolio snapshot:\n{facts}"},
                    ],
                    "max_tokens":  280,
                    "temperature": 0.2,
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            text = (
                payload.get("choices", [{}])[0].get("message", {}).get("content")
                or payload.get("output", [{}])[0].get("content", [{}])[0].get("text")
                or ""
            ).strip()
            return {"narrative": text, "facts": facts}
    except Exception as e:
        # Fail open: if the FM call errors, return a deterministic fallback so the dashboard still renders.
        fallback = (
            f"The {scope} covers {facts['total_assets']} assets with "
            f"{facts['critical_count']} Critical and {facts['poor_count']} Poor ratings. "
            f"{facts['overdue_count']} inspections are overdue (avg {facts['avg_days_overdue']} days) "
            f"with ${int(facts['overdue_cost_exposure']):,} in repair exposure, and "
            f"{facts['overdue_and_safety']} assets are both overdue and safety-flagged. "
            f"Prioritize re-inspection of the overdue + safety-flagged cohort before addressing the remaining backlog."
        )
        return {"narrative": fallback, "facts": facts, "fallback": True, "error": str(e)[:200]}


# ---------------------------------------------------------------------------
# Asset search / list — used by the drawer and the Assets tab
# ---------------------------------------------------------------------------

@router.get("/assets/search")
async def search_assets(
    q: str = Query("", max_length=200),
    region: str = "",
    discipline: str = "",
    condition: str = "",
    client: str = "",
):
    extra = ""
    if q:
        safe_q = q.replace("'", "''").lower()
        safe_up = q.replace("'", "''").upper()
        extra = (
            f"LOWER(project_name) LIKE '%{safe_q}%' "
            f"OR LOWER(location) LIKE '%{safe_q}%' "
            f"OR LOWER(key_findings) LIKE '%{safe_q}%' "
            f"OR report_id LIKE '%{safe_up}%'"
        )
    where = build_where(region, discipline, condition, client, extra=extra)
    rows = await run_query(f"""
        SELECT
            report_id             AS asset_id,
            project_name          AS asset_name,
            inspection_type       AS asset_type,
            state                 AS region,
            state,
            condition_rating,
            condition_category,
            overdue               AS inspection_overdue,
            estimated_repair_cost AS estimated_maintenance_cost,
            inspection_date       AS last_inspection_date
        FROM {TABLE}
        {where}
        ORDER BY priority_score DESC
        LIMIT 100
    """)
    return [_cast_row(r) for r in rows]
