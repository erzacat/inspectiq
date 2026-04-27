import os, time

_host_raw = os.environ.get("DATABRICKS_HOST", "https://e2-demo-field-eng.cloud.databricks.com").rstrip("/")
WORKSPACE_HOST = _host_raw if _host_raw.startswith("http") else f"https://{_host_raw}"
WAREHOUSE_ID   = os.environ.get("DATABRICKS_WAREHOUSE_ID", "4b9b953939869799")

_token_cache: dict = {"token": "", "expires": 0}

def get_token() -> str:
    # 1. Explicit env var (set by some Databricks App runtimes)
    env = os.environ.get("DATABRICKS_TOKEN", "")
    if env:
        return env

    # 2. Databricks SDK auto-auth (works with app service principal OAuth)
    if time.time() < _token_cache["expires"] - 60:
        return _token_cache["token"]
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        headers = w.config.authenticate()
        token = headers.get("Authorization", "").replace("Bearer ", "")
        if token:
            _token_cache["token"] = token
            _token_cache["expires"] = time.time() + 3000
            return token
    except Exception:
        pass

    # 3. Local dev fallback — CLI token
    try:
        import json, subprocess
        r = subprocess.run(
            ["databricks", "auth", "token", "--profile=e2-demo-west"],
            capture_output=True, text=True, timeout=10,
        )
        d = json.loads(r.stdout)
        _token_cache["token"] = d["access_token"]
        _token_cache["expires"] = time.time() + d.get("expires_in", 3600)
        return _token_cache["token"]
    except Exception:
        pass

    return ""

def get_workspace_host() -> str:
    return WORKSPACE_HOST
