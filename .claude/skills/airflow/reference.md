# Reference

Operational detail referenced from [SKILL.md](SKILL.md), loaded only when needed, such as debugging a live DAG.

## Debugging via the REST API

Resolve credentials from a password manager; never hardcode them or ask the user to paste them. Airflow 3 auth is JWT via `POST /auth/token`; use `/api/v2` and pass the token as `Authorization: Bearer`.

Read the `1password-cli` skill and pin `OP_ACCOUNT` on every secret-reading `op` call. Take `AIRFLOW_HOST`, `AIRFLOW_USER`, and `AIRFLOW_PASSWORD` from the user's `~/.env.op` mapping; do not guess credential item IDs. Inject credentials into Python:

```bash
op --account "$OP_ACCOUNT" run --env-file="$HOME/.env.op" -- python3 script.py
```

Keep resolved credentials and the JWT inside the subprocess. Never print them or put them in command arguments or tracked files. Fetch one token per investigation script and reuse it for its requests. `ctx_batch_execute` takes `commands` as a JSON array of `{label, command}` objects, not a stringified list.

### Read-only investigation example

Save this as a temporary script and replace the generic DAG/run/task identifiers. It authenticates, URL-encodes run IDs (including `+`), and reads one mapped task's current state and attempt history. Print narrow projections rather than whole responses.

```python
import json
import os
from urllib.parse import quote
from urllib.request import Request, urlopen

host = os.environ["AIRFLOW_HOST"].rstrip("/")
credentials = json.dumps({
    "username": os.environ["AIRFLOW_USER"],
    "password": os.environ["AIRFLOW_PASSWORD"],
}).encode()
with urlopen(Request(host + "/auth/token", data=credentials,
                     headers={"Content-Type": "application/json"}), timeout=30) as response:
    token = json.load(response)["access_token"]

def get(path):
    request = Request(host + "/api/v2/" + path,
                      headers={"Authorization": "Bearer " + token})
    with urlopen(request, timeout=45) as response:
        return json.load(response)

dag_id = "example_dag"
run_id = "manual__YYYY-MM-DDTHH:MM:SS+00:00"
task_id = "example_task"
map_index = 0
base = f"dags/{quote(dag_id, safe='')}/dagRuns/{quote(run_id, safe='')}"
task_path = f"{base}/taskInstances/{quote(task_id, safe='')}/{map_index}"
fields = ("task_id", "map_index", "state", "try_number", "max_tries",
          "start_date", "end_date", "dag_version")
print("version", get("version"))
current = get(task_path)
print("current", {key: current.get(key) for key in fields})
history = get(task_path + "/tries")
for attempt in history["task_instances"]:
    print("attempt", {key: attempt.get(key) for key in fields})
```

### Investigation endpoints

Paths below are relative to `/api/v2`. Encode each path identifier separately. For unmapped task detail/history omit the `/{map_index}` path segment; for logs pass the mapped index explicitly as a query parameter.

| Evidence | GET endpoint |
|---|---|
| Actual server version | `/version` |
| Recent or queued/running runs | `/dags/{dag_id}/dagRuns?limit=100&offset=0&order_by=-run_after` |
| Run state, parameters, and version metadata | `/dags/{dag_id}/dagRuns/{run_id}` |
| Current task definition, including `retries` and `retry_delay` | `/dags/{dag_id}/tasks/{task_id}` |
| All task instances and stored retry allowances in a run | `/dags/{dag_id}/dagRuns/{run_id}/taskInstances?limit=100&offset=0` |
| One mapped task instance | `/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/{map_index}` |
| Mapped task attempt history | `/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/{map_index}/tries` |
| Parsed DAG versions | `/dags/{dag_id}/dagVersions` |
| Audit events, including manual clears | `/eventLogs?dag_id={dag_id}&limit=100&offset=0&order_by=-when` |
| Task attempt log | `/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}?map_index={map_index}` |
| Return XCom | `/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/xcomEntries/return_value?deserialize=true` |

Paginate collections with `limit`/`offset` until `total_entries` is covered, or stop at the investigation's relevant date range. API state filters use repeated parameters (`state=running&state=queued`), not comma-separated values. Match audit events to the exact run and map index; clear events can have a null top-level map index and identify tasks in their `extra` JSON. A later success or an increased try number alone does not prove automatic retry: check for `post_clear_task_instances` events between attempts.

Logs default to JSON with `content` as a list of event objects, not a string. Pass `map_index` for mapped tasks (the default is `-1`). Follow `continuation_token` using a URL-encoded `token` query parameter until empty. Use `full_content=true` only for short logs; large logs are buffered server-side.

### DAG run notes

Notes are attached to individual DAG runs. Read the `note` field from GET
`/api/v2/dags/{dag_id}/dagRuns/{run_id}`. Useful content includes why a run was
triggered or replaced, a ticket/MR link, and the related run ID.

Set an initial note when triggering a run: include `note` alongside `conf` and
`logical_date` in POST `/api/v2/dags/{dag_id}/dagRuns`. For a manual run with no
logical date, pass `"logical_date": null` explicitly.

Update an existing run's note with PATCH
`/api/v2/dags/{dag_id}/dagRuns/{run_id}?update_mask=note` and this JSON body:

```json
{"note": "Reason for this run; related ticket or run ID."}
```

Encode the run ID as a path component, including `+` as `%2B`. Send only `note`
when updating a note; adding `state` would request a separate state change.
PATCH replaces the existing note, so read it first and preserve useful context.
On Airflow 3.2.1, PATCH notes are limited to 1,000 characters. The response is a
single DAG-run object; verify its `note` field. Writing a note is a mutation and
requires user authorization. The same PATCH can include a note with an already
authorized run-state change to record its reason.

### Mutations and dry runs

Clearing/retrying task instances, deleting runs, triggering runs, and pausing DAGs require explicit approval before a mutating call. A dry-run preview may proceed during investigation. Show the exact run/task/map-index selection and matched count before asking to execute it. Do not clear running, successful, or unrelated tasks to refresh retry settings.

For a targeted clear preview, POST to `/api/v2/dags/{dag_id}/clearTaskInstances` with `Content-Type: application/json` and a body such as:

```json
{
  "dag_run_id": "example_run_id",
  "task_ids": [["example_task", 0]],
  "only_failed": true,
  "include_downstream": false,
  "include_upstream": false,
  "include_future": false,
  "include_past": false,
  "dry_run": true
}
```

After authorization, repeat the same clear request with `"dry_run": false` to execute it. `task_ids: [["example_task", 0]]` selects one mapped instance; `task_ids: ["example_task"]` selects all mapped instances of that task. Use `"only_failed": false` when the requested selection includes other states. The response contains `task_instances` and `total_entries`; read the selected instances again to check their current state. Clearing allows tasks to run again, and `reset_dag_runs` defaults to true.

### Delete DAG runs

DELETE `/api/v2/dags/{dag_id}/dagRuns/{run_id}` deletes one run. For multiple runs, resolve the requested selection into run IDs, paginate the run listing if needed, and issue DELETE for each ID. URL-encode each identifier separately. A successful DELETE returns HTTP 204 with an empty body; do not attempt to parse it as JSON. Verify with GET on the same path: HTTP 404 means the run is absent.

This example reuses `host` and `token` from the authentication example above. Fill in the requested run IDs and execute after authorization:

```python
from urllib.error import HTTPError

run_ids = ["manual__YYYY-MM-DDTHH:MM:SS+00:00"]
for run_id in run_ids:
    path = f"dags/{quote(dag_id, safe='')}/dagRuns/{quote(run_id, safe='')}"
    request = Request(host + "/api/v2/" + path, method="DELETE",
                      headers={"Authorization": "Bearer " + token})
    try:
        with urlopen(request, timeout=45) as response:
            assert response.status == 204
    except HTTPError as error:
        if error.code != 404:
            raise
    try:
        get(path)
    except HTTPError as error:
        if error.code != 404:
            raise
        print(run_id, "absent")
    else:
        raise RuntimeError(f"Run still exists: {run_id}")
```

### Mark tasks success or failed

PATCH `/api/v2/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/{map_index}` with `Content-Type: application/json` and this body:

```json
{
  "new_state": "success",
  "include_upstream": false,
  "include_downstream": false,
  "include_future": false,
  "include_past": false
}
```

Use `"new_state": "failed"` to mark failed. The field is `new_state`, not `state`. For an unmapped task omit `/{map_index}`; for a mapped task omitting it targets all indices. Preview the same PATCH using a `/dry_run` suffix; execute on the original path after authorization. This PATCH has no `dry_run` body field. Its response contains `task_instances` and `total_entries`; verify the selected instances with GET. Marking success changes metadata without executing the task.

Airflow 3.2.1 request fields and routes: [task-instance models](https://github.com/apache/airflow/blob/3.2.1/airflow-core/src/airflow/api_fastapi/core_api/datamodels/task_instances.py), [task-instance routes](https://github.com/apache/airflow/blob/3.2.1/airflow-core/src/airflow/api_fastapi/core_api/routes/public/task_instances.py).
