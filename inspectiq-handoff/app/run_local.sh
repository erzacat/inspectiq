#!/bin/bash
# Run InspectIQ locally — token auto-refreshes via databricks CLI (mbi-demo profile)
cd "$(dirname "$0")"

export AGENT_ENDPOINT="https://adb-7405610014970746.6.azuredatabricks.net/serving-endpoints/mbi-inspectiq-supervisor-v3/invocations"
export WAREHOUSE_ID="6bc4bd454fa471ce"

echo "InspectIQ running at http://localhost:8000"
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
