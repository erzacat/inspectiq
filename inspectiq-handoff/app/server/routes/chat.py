import os, json, contextlib
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import AsyncGenerator
import httpx
from server.config import get_workspace_host, get_token

# ---------------------------------------------------------------------------
# MLflow tracing
# ---------------------------------------------------------------------------
# Sends a hierarchical trace to the configured experiment every time someone
# queries the AI Assistant. Fails open — if MLflow is mis-configured or
# unreachable, chat still works, it just doesn't emit traces.

_MLFLOW_ENABLED = False
try:
    import mlflow
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "databricks"))
    _exp_id = os.environ.get("MLFLOW_EXPERIMENT_ID")
    if _exp_id:
        mlflow.set_experiment(experiment_id=_exp_id)
    _MLFLOW_ENABLED = True
    print(f"[chat] MLflow tracing enabled; experiment_id={_exp_id}")
except Exception as e:
    print(f"[chat] MLflow tracing disabled: {e}")

def _trace(name: str, span_type: str = "CHAIN"):
    """No-op decorator when MLflow is not available."""
    def decorator(fn):
        if not _MLFLOW_ENABLED:
            return fn
        return mlflow.trace(name=name, span_type=span_type)(fn)
    return decorator


router = APIRouter()

VS_INDEX  = "mbi_demo.inspectiq.doc_index"
LLM_MODEL = os.environ.get("SERVING_ENDPOINT", "databricks-claude-sonnet-4-5")
WH_ID     = os.environ.get("WAREHOUSE_ID", "4b9b953939869799")

# Feature flag — when true, bypass the in-app RAG+SQL router and call the deployed
# supervisor agent endpoint (mbi-inspectiq-supervisor) instead. Flip in app.yaml to revert.
USE_SUPERVISOR  = os.environ.get("USE_SUPERVISOR", "false").lower() in ("1", "true", "yes")
AGENT_ENDPOINT  = os.environ.get("AGENT_ENDPOINT", "").strip()

SQL_KEYWORDS = (
    "how many", "count", "total", "average", "percentage", "percent",
    "by region", "by state", "by type", "by discipline",
    "list all", "show all", "top 10", "top 5", "top 15",
    "highest", "lowest", "worst rated", "best rated",
    "maintenance backlog", "repair cost", "cost",
    "overdue inspection", "overdue rate",
    "condition category", "condition rating",
    "breakdown", "distribution", "trend by", "ranking",
    "how much", "which assets", "which projects",
)

DOC_KEYWORDS = (
    "inspection report", "rpt-", "finding", "deficiency", "defect",
    "crack", "cracking", "corrosion", "spalling", "delamination",
    "recommendation", "repair procedure", "repair method",
    "rebar exposure", "rebar", "freeze-thaw", "freeze thaw",
    "rutting", "pavement distress", "surface distress", "alligator",
    "fatigue", "scour", "section loss", "bearing",
    "structural steel", "concrete", "asphalt", "pavement",
    "emergency", "safety risk", "immediate",
    "according to the report", "what did the inspection",
    "what were the findings", "what issues", "what defects",
    "epoxy injection", "patch repair", "sealant", "milling",
)


@_trace(name="classify_intent", span_type="TOOL")
def classify_intent(question: str) -> str:
    q = question.lower()
    sql_score = sum(1 for kw in SQL_KEYWORDS if kw in q)
    doc_score = sum(1 for kw in DOC_KEYWORDS if kw in q)
    if sql_score > 0 and doc_score > 0:
        return "both"
    if sql_score > doc_score:
        return "sql"
    if doc_score > 0:
        return "doc"
    return "doc"


SYSTEM_PROMPT = """You are InspectIQ, an intelligent infrastructure knowledge assistant for Michael Baker International.

You help engineers, inspectors, project managers, and executives find answers from infrastructure inspection reports covering structural steel, concrete, and asphalt/pavement disciplines.

**Guidelines:**
- Always cite your sources using the document reference found in the retrieved content.
- Be specific and technical — your audience includes licensed PEs and field inspectors.
- If the retrieved documents don't contain a direct answer, say so clearly.
- Use the 1–5 condition rating scale (1=worst, 5=best) for this portfolio.
- Organize longer answers with headings or bullet points."""

DOC_SYSTEM = """You are the Document Search Agent for InspectIQ.
Synthesize retrieved MBI infrastructure inspection reports covering structural steel, concrete, and asphalt/pavement assessments.
ALWAYS cite document references found in the retrieved content for every factual claim.
Use the 1–5 condition rating scale (1=worst, 5=best).
If no relevant documents are found, say so clearly."""

SQL_SYSTEM = """You are the Asset Intelligence Agent for InspectIQ.
Present structured asset database results clearly for infrastructure managers.
Express costs in "$X.XM" format for millions. Include asset counts alongside percentages.
Sort by risk severity (worst first) by default. End with a brief executive takeaway."""


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = True


@_trace(name="vector_search", span_type="RETRIEVER")
async def vector_search(query: str, k: int = 5) -> list[dict]:
    host = get_workspace_host()
    token = get_token()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{host}/api/2.0/vector-search/indexes/{VS_INDEX}/query",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "query_text": query,
                "columns": ["chunk_id", "doc_id", "discipline", "content"],
                "num_results": k,
            },
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        cols = [c["name"] for c in data.get("manifest", {}).get("columns", [])]
        return [dict(zip(cols, row)) for row in data.get("result", {}).get("data_array", [])]


@_trace(name="run_sql", span_type="TOOL")
async def run_sql(sql: str) -> str:
    host = get_workspace_host()
    token = get_token()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{host}/api/2.0/sql/statements",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"statement": sql, "warehouse_id": WH_ID,
                  "wait_timeout": "30s", "on_wait_timeout": "CANCEL",
                  "disposition": "INLINE", "format": "JSON_ARRAY"},
        )
    data = resp.json()
    if data.get("status", {}).get("state") != "SUCCEEDED":
        return "Query error: " + str(data.get("status", {}).get("error", "unknown"))[:200]
    cols = [c["name"] for c in data.get("manifest", {}).get("schema", {}).get("columns", [])]
    rows = data.get("result", {}).get("data_array", []) or []
    if not rows:
        return "No results."
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for row in rows[:25]:
        lines.append("| " + " | ".join(str(v) if v is not None else "" for v in row) + " |")
    if len(rows) > 25:
        lines.append(f"*...{len(rows)-25} more rows*")
    return "\n".join(lines)


@_trace(name="get_sql_context", span_type="CHAIN")
async def get_sql_context(question: str) -> str:
    host = get_workspace_host()
    token = get_token()
    sql_prompt = [
        {"role": "system", "content": (
            "You are a Databricks SQL expert. Write ONE SQL query (no markdown, no explanation) "
            "to answer the user's question using this table:\n\n"
            "Table: mbi_demo.inspectiq.project_assets\n"
            "Columns and their EXACT stored values:\n"
            "  - report_id           STRING  (e.g., 'INS-SS-001', 'INS-CO-002', 'INS-AP-003')\n"
            "  - project_name        STRING\n"
            "  - inspection_type     STRING  — exactly one of: 'Structural Steel', 'Concrete', 'Asphalt'\n"
            "  - state               STRING  — TWO-LETTER US CODE ONLY: 'PA', 'NJ', 'DE', 'MD', 'VA', 'NY'\n"
            "                                  NEVER spell out state names. 'Pennsylvania' → 'PA'.\n"
            "  - location            STRING  — city name (e.g., 'Philadelphia', 'Pittsburgh')\n"
            "  - inspector           STRING\n"
            "  - inspection_date     DATE\n"
            "  - next_inspection_date DATE\n"
            "  - condition_rating    INT     — 1 (worst) to 9 (best), FHWA scale\n"
            "  - condition_category  STRING  — exactly one of: 'Critical', 'Poor', 'Fair', 'Good'\n"
            "  - priority            STRING  — exactly one of: 'Critical', 'High', 'Medium', 'Low'\n"
            "  - overdue             BOOLEAN — use `overdue = true` (not 'true' as string)\n"
            "  - safety_flagged      BOOLEAN — use `safety_flagged = true`\n"
            "  - nbis_deficient      BOOLEAN — use `nbis_deficient = true`\n"
            "  - priority_score      DOUBLE  — composite urgency score\n"
            "  - estimated_repair_cost BIGINT — USD\n"
            "  - key_findings        STRING  — free-text\n"
            "  - finding_count       INT\n\n"
            "Critical rules:\n"
            "  1. ONLY return SQL — no markdown fences, no explanation, no preamble.\n"
            "  2. For state filters: always use the 2-letter code. If the user writes a full state name, map it ('Pennsylvania'→'PA', 'New Jersey'→'NJ', 'Delaware'→'DE', 'Maryland'→'MD', 'Virginia'→'VA', 'New York'→'NY').\n"
            "  3. For boolean filters: use `= true` / `= false`, never string literals.\n"
            "  4. For repair costs: ROUND(SUM(estimated_repair_cost)/1e6, 2) AS cost_millions.\n"
            "  5. LIMIT 25 unless the query is an aggregate (COUNT, SUM, AVG, etc.).\n"
            "  6. Match category/type values exactly as listed above (case-sensitive)."
        )},
        {"role": "user", "content": question},
    ]
    async with httpx.AsyncClient(timeout=30) as client:
        gen_resp = await client.post(
            f"{host}/serving-endpoints/{LLM_MODEL}/invocations",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"messages": sql_prompt, "max_tokens": 512},
        )
    if gen_resp.status_code != 200:
        return f"SQL generation error: HTTP {gen_resp.status_code}"
    sql = gen_resp.json()["choices"][0]["message"]["content"].strip()
    if "```" in sql:
        parts = sql.split("```")
        for part in parts:
            stripped = part.strip()
            if stripped.lower().startswith("sql"):
                stripped = stripped[3:].lstrip("\n").strip()
            upper = stripped.upper()
            if upper.startswith("SELECT") or upper.startswith("WITH"):
                sql = stripped
                break
    sql = sql.strip()
    table_results = await run_sql(sql)
    return f"**Query:**\n```sql\n{sql}\n```\n\n**Results:**\n{table_results}"


def build_doc_messages(question: str, docs: list[dict], history: list[dict]) -> list[dict]:
    context = "\n\n".join(
        f"[{d.get('doc_id', '?')} | {d.get('discipline', '?')}]\n{d.get('content', '')}"
        for d in docs
    )
    msgs = [{"role": "system", "content": DOC_SYSTEM}] + history
    msgs.append({"role": "user", "content": (
        f"Retrieved inspection report excerpts:\n\n{context}\n\n---\n\n"
        f"Question: {question}\n\nAnswer with document citations."
    )})
    return msgs


def build_sql_messages(question: str, sql_results: str, history: list[dict]) -> list[dict]:
    msgs = [{"role": "system", "content": SQL_SYSTEM}] + history
    msgs.append({"role": "user", "content": (
        f"Asset database results:\n\n{sql_results}\n\n---\n\n"
        f"User question: {question}\n\nProvide a clear, actionable response."
    )})
    return msgs


def build_combined_messages(question: str, docs: list[dict], sql_results: str, history: list[dict]) -> list[dict]:
    doc_text = "\n\n".join(
        f"[{d.get('doc_id', '?')} | {d.get('discipline', '?')}]\n{d.get('content', '')}"
        for d in docs
    )
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    msgs.append({"role": "user", "content": (
        f"## Structured Data Results\n{sql_results}\n\n"
        f"## Document Search Results\n{doc_text}\n\n---\n\n"
        f"Question: {question}\n\nProvide a comprehensive answer using both sources. "
        "Cite document references for report-based claims."
    )})
    return msgs


@_trace(name="build_llm_messages", span_type="CHAIN")
async def _get_llm_messages(question: str, history: list[dict]) -> list[dict]:
    intent = classify_intent(question)
    if intent == "sql":
        sql_results = await get_sql_context(question)
        return build_sql_messages(question, sql_results, history)
    elif intent == "both":
        docs = await vector_search(question, k=4)
        sql_results = await get_sql_context(question)
        return build_combined_messages(question, docs, sql_results, history)
    else:
        docs = await vector_search(question, k=5)
        return build_doc_messages(question, docs, history)


async def stream_rag_response(messages: list[dict]) -> AsyncGenerator[str, None]:
    """
    Streams the LLM response as one MLflow trace. The root span is opened as a context
    manager so that child spans (`classify_intent`, `vector_search`, `run_sql`,
    `get_sql_context`, `build_llm_messages`) nest under it instead of each becoming its
    own root trace. Without the `with` form, only the root is set active and decorated
    child calls are re-rooted — producing the "2 traces per question" symptom.
    """
    user_question = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    history = [m for m in messages[:-1] if m["role"] in ("user", "assistant")]

    # If MLflow tracing is disabled, degrade to a no-op span so the code path is identical.
    @contextlib.asynccontextmanager
    async def _root_span():
        if not _MLFLOW_ENABLED:
            class _Noop:
                def set_inputs(self, *_a, **_k): pass
                def set_outputs(self, *_a, **_k): pass
            yield _Noop()
            return
        with mlflow.start_span(name="ai_assistant_chat", span_type="AGENT") as s:
            try:
                s.set_inputs({"question": user_question, "history_len": len(history)})
            except Exception:
                pass
            yield s

    async with _root_span() as span:
        intent = classify_intent(user_question)
        if intent == "sql":
            yield "data: " + json.dumps({"content": "*Querying asset database...*\n\n"}) + "\n\n"
        elif intent == "both":
            yield "data: " + json.dumps({"content": "*Searching reports and querying asset database...*\n\n"}) + "\n\n"

        try:
            rag_msgs = await _get_llm_messages(user_question, history)
        except Exception as e:
            yield "data: " + json.dumps({"content": f"Error preparing context: {e}"}) + "\n\n"
            yield "data: [DONE]\n\n"
            try: span.set_outputs({"error": str(e)})
            except Exception: pass
            return

        full_response: list[str] = []
        host = get_workspace_host()
        token = get_token()

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{host}/serving-endpoints/{LLM_MODEL}/invocations",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={"messages": rag_msgs, "max_tokens": 2048, "stream": True},
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        err = f"LLM error {resp.status_code}: {body.decode()[:200]}"
                        yield "data: " + json.dumps({"content": err}) + "\n\n"
                        yield "data: [DONE]\n\n"
                        try: span.set_outputs({"error": err})
                        except Exception: pass
                        return

                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:]
                        if raw == "[DONE]":
                            yield "data: [DONE]\n\n"
                            try: span.set_outputs({"response": "".join(full_response), "intent": intent})
                            except Exception: pass
                            return
                        try:
                            chunk_data = json.loads(raw)
                            delta = chunk_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                full_response.append(delta)
                                yield "data: " + json.dumps({"content": delta}) + "\n\n"
                        except Exception:
                            pass

                    yield "data: [DONE]\n\n"
                    try: span.set_outputs({"response": "".join(full_response), "intent": intent})
                    except Exception: pass

            except Exception as e:
                yield "data: " + json.dumps({"content": f"Stream error: {e}"}) + "\n\n"
                yield "data: [DONE]\n\n"
                try: span.set_outputs({"error": str(e)})
                except Exception: pass


async def call_supervisor(messages: list[dict]) -> str:
    """Call the deployed mbi-inspectiq-supervisor agent endpoint and return the final answer text.

    The supervisor was logged as an MLflow pyfunc with a pandas-DataFrame signature where each
    row's `messages` column is a list of {role, content} dicts. Databricks serving accepts this
    via `dataframe_records` payloads. Falls back to the `inputs` format if the endpoint rejects
    the first shape.
    """
    if not AGENT_ENDPOINT:
        raise RuntimeError("USE_SUPERVISOR=true but AGENT_ENDPOINT is not set")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=180) as client:
        # Primary: pyfunc DataFrame signature
        resp = await client.post(
            AGENT_ENDPOINT,
            headers=headers,
            json={"dataframe_records": [{"messages": messages}]},
        )
        if resp.status_code != 200:
            # Fallback: inputs format
            resp = await client.post(
                AGENT_ENDPOINT,
                headers=headers,
                json={"inputs": {"messages": [messages]}},
            )
        resp.raise_for_status()
        payload = resp.json()

    preds = payload.get("predictions")
    if isinstance(preds, list) and preds:
        first = preds[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("content") or first.get("output") or json.dumps(first)
    if "output" in payload:
        return str(payload["output"])
    return json.dumps(payload)


async def stream_supervisor_response(messages: list[dict]) -> AsyncGenerator[str, None]:
    """Supervisor endpoint returns a single final message; emit it as one SSE delta so the
    existing streaming UI still works. Yields an error message in-band on failure."""
    try:
        answer = await call_supervisor(messages)
    except Exception as e:
        answer = f"Supervisor endpoint error: {e}"
    yield f"data: {json.dumps({'content': answer})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(req: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    # Feature-flag branch: route to the deployed supervisor agent endpoint
    if USE_SUPERVISOR:
        if req.stream:
            return StreamingResponse(
                stream_supervisor_response(messages),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        try:
            content = await call_supervisor(messages)
            return {"content": content}
        except Exception as e:
            return {"content": f"Supervisor endpoint error: {e}"}

    # Default branch: in-app RAG+SQL router (current behavior)
    if req.stream:
        return StreamingResponse(
            stream_rag_response(messages),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    user_question = messages[-1]["content"]
    history = messages[:-1]
    try:
        rag_msgs = await _get_llm_messages(user_question, history)
    except Exception as e:
        return {"content": f"Error: {e}"}

    host = get_workspace_host()
    token = get_token()
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{host}/serving-endpoints/{LLM_MODEL}/invocations",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"messages": rag_msgs, "max_tokens": 2048},
        )
        resp.raise_for_status()
        return {"content": resp.json()["choices"][0]["message"]["content"]}


@router.get("/chat/health")
async def health():
    return {
        "status":         "ok",
        "vs_index":       VS_INDEX,
        "llm":            LLM_MODEL,
        "use_supervisor": USE_SUPERVISOR,
        "agent_endpoint": AGENT_ENDPOINT if USE_SUPERVISOR else None,
    }
