# Reference

Operational detail referenced from [SKILL.md](SKILL.md), loaded only when actually needed (e.g. while debugging a live DAG).

## Debugging via the REST API

Resolve credentials from a password manager - never hardcode them, never prompt the user to paste them. Airflow 3 auth is JWT via `POST /auth/token`; pass the token as `Authorization: Bearer`. `/api/v1` is gone - use `/api/v2`.

```bash
# Get a token (username/password piped via stdin, not argv, so they don't leak to `ps aux`)
TOKEN=$(curl -fsS --data-binary @- -H "Content-Type: application/json" \
  -X POST "$AIRFLOW_HOST/auth/token" <<< "{\"username\":\"$AIRFLOW_USER\",\"password\":\"$AIRFLOW_PASSWORD\"}" \
  | jq -re '.access_token')

# Trigger a DAG run
curl -fsS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"conf":{}}' "$AIRFLOW_HOST/api/v2/dags/$DAG_ID/dagRuns"

# Clear/retry a task instance (dry_run defaults true - confirm with the user before dry_run:false)
curl -fsS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"only_failed":true,"dry_run":true,"dag_run_id":"'"$RUN_ID"'"}' \
  "$AIRFLOW_HOST/api/v2/dags/$DAG_ID/clearTaskInstances"

# Fetch task logs (JSON by default; content is a list of events, not a string)
curl -fsS -H "Authorization: Bearer $TOKEN" \
  "$AIRFLOW_HOST/api/v2/dags/$DAG_ID/dagRuns/$RUN_ID/taskInstances/$TASK_ID/logs/$TRY_NUMBER"

# Fetch an XCom value
curl -fsS -H "Authorization: Bearer $TOKEN" \
  "$AIRFLOW_HOST/api/v2/dags/$DAG_ID/dagRuns/$RUN_ID/taskInstances/$TASK_ID/xcomEntries/return_value?deserialize=true"
```

Guardrails: clearing/retrying task instances, deleting runs, and pausing DAGs are destructive - always confirm with the user before running them with a non-dry-run/mutating payload.
