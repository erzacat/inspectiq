"""
InspectIQ — Michael Baker International
Databricks App: multi-discipline inspection intelligence platform
"""

import os
import sys
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

try:
    from server.routes.chat import router as chat_router
except Exception as e:
    print(f"STARTUP ERROR: failed to import chat router: {e}", file=sys.stderr)
    raise

try:
    from server.routes.assets import router as assets_router
except Exception as e:
    print(f"STARTUP ERROR: failed to import assets router: {e}", file=sys.stderr)
    raise

app = FastAPI(title="InspectIQ — Michael Baker International")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(assets_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "InspectIQ"}


@app.get("/api/debug")
async def debug():
    """Diagnostic endpoint — shows env vars and tests backend connectivity."""
    import httpx
    from server.config import get_workspace_host, get_token, WAREHOUSE_ID
    info = {
        "DATABRICKS_HOST": os.environ.get("DATABRICKS_HOST", "NOT SET"),
        "DATABRICKS_TOKEN": "SET" if os.environ.get("DATABRICKS_TOKEN") else "NOT SET",
        "WORKSPACE_HOST_USED": get_workspace_host(),
        "WAREHOUSE_ID": WAREHOUSE_ID,
    }
    # Test SQL connectivity
    try:
        host = get_workspace_host()
        token = get_token()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{host}/api/2.0/sql/statements",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"statement": "SELECT 1 AS test", "warehouse_id": WAREHOUSE_ID,
                      "wait_timeout": "10s", "format": "JSON_ARRAY"},
            )
            info["sql_status"] = resp.status_code
            info["sql_body"] = resp.text[:500]
    except Exception as e:
        info["sql_error"] = str(e)
    # Test VS connectivity
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{host}/api/2.0/vector-search/indexes/mbi_demo.inspectiq.doc_index/query",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"query_text": "test", "columns": ["chunk_id"], "num_results": 1},
            )
            info["vs_status"] = resp.status_code
            info["vs_body"] = resp.text[:300]
    except Exception as e:
        info["vs_error"] = str(e)
    return info


# Serve React frontend without aiofiles dependency
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DIST_DIR  = os.path.join(BASE_DIR, "frontend", "dist")

MIME_TYPES = {
    ".js":   "application/javascript",
    ".css":  "text/css",
    ".html": "text/html",
    ".svg":  "image/svg+xml",
    ".ico":  "image/x-icon",
    ".png":  "image/png",
    ".woff2": "font/woff2",
    ".woff":  "font/woff",
}


@app.get("/{full_path:path}")
async def serve_spa(full_path: str, request: Request):
    # Try to serve a real file from dist/
    candidate = os.path.join(DIST_DIR, full_path)
    if os.path.isfile(candidate):
        ext = os.path.splitext(candidate)[1]
        media_type = MIME_TYPES.get(ext, "application/octet-stream")
        return FileResponse(candidate, media_type=media_type)

    # Fall back to index.html for SPA routing
    index = os.path.join(DIST_DIR, "index.html")
    if os.path.isfile(index):
        return FileResponse(index, media_type="text/html")

    return JSONResponse(
        {"status": "ok", "app": "InspectIQ API — build the frontend to see the UI"},
        status_code=200,
    )
