---
name: airflow
description: Use when authoring, reviewing, debugging, testing, or operating Apache Airflow DAGs, tasks, sensors, operators, scheduling, XComs, or task mapping.
---

# Authoring principles

- A task in Airflow should be a small idempotent piece of work that can be retried without side effects. For example before using a for loop over a list inside a task consider the use of expand to run a TI per element as it makes retries cleaner.
- Any `@task` used with `.expand()` needs `map_index_template` set, e.g. `map_index_template="""{{ task.parameters['date'] }}"""`, so each mapped instance shows a readable name in the UI instead of a bare index.
- Always consider side effects of a retry -> alerts, writes to a sink etc
- Use `max_active_tis_per_dag` to cap concurrent instances of one mapped task - across active runs of the DAG, not just within one run. See "Serializing mapped instances" below for the `1`-instance case.
- Use DAG-level `max_active_tasks` to cap the number of concurrent task instances within a single DAG run. It does not limit concurrency across separate active runs of the same DAG - for a shared limit across runs, or across different DAGs entirely, use an Airflow Pool instead.
- Use `get_current_context` inside the task body instead of passing context variables such as `logical_date` as a parameter to a task. Returning an XCom is used to pass data owned by a task to a consumer, if a value can be inferred from Airflow variables or context then it shouldn't be passed as an argument. A task should only hand XComs to a consumer that it cannot compute itself and only the XComs it needs.
- Prefer TaskFlow decorators (`@task`, `@task.sensor`, `@task.branch`, `@task.short_circuit`, `@task_group`) for custom Python task logic; use purpose-built Airflow/provider operators and sensors when one already implements the required external-system behavior (e.g. `TriggerDagRunOperator`) rather than reimplementing it as a `@task`. Define the DAG itself with `with DAG(...)` syntax.
- For the `schedule` parameter in the `DAG` definition default to `CronTriggerTimetable`
- Default a DAG to `max_active_runs=1` unless the DAG is specifically designed to have multiple runs in flight at once (e.g. independent per-partition backfills). Most DAGs assume the previous run's state/side effects are settled before the next one starts; without this cap, a slow run plus a normal schedule cadence can pile up overlapping runs that race each other.

See "Personal conventions" below for team style choices (inline-vs-function, pendulum, `typing`, etc) that are not Airflow requirements.

# Retries and backoff

- Task-level: `retries` (attempt count), `retry_delay` (base delay, a `timedelta`), `retry_exponential_backoff` (bool), `max_retry_delay` (cap on the computed delay). Set sane defaults in the DAG's `default_args` and override per-task only where a specific task needs different behavior - see "Serializing mapped instances" below for one such case (`retries=0`).
- With `retry_exponential_backoff=True`, each retry's wait grows roughly exponentially off `retry_delay` (not a fixed increment), a deterministic (hash-based, not random) jitter is added on top, and the result is capped at `max_retry_delay`. The exact arithmetic has changed across Airflow versions and is easy to misstate from memory - check `next_retry_datetime` in the installed Airflow's `taskinstance.py` if the precise formula matters for a specific case, rather than trusting a hardcoded formula here.
- Don't hand-roll a sleep/backoff loop inside a task body to work around a flaky dependency - use these operator-level knobs instead so retry behavior stays visible in the UI and consistent with the rest of the DAG.

# Serializing mapped instances

`max_active_tis_per_dag=1` on a mapped (`.expand()`-ed) task holds each instance for its full runtime, not only at start - the next instance cannot begin until the current one ends (see "Authoring principles" above for the cross-run scope of this cap). Reach for this when instances must run strictly one after another rather than just capped in number. Neither `TaskGroup` nor `@task_group` has an equivalent throttle for its own expanded children, so this task-level setting is the only lever.

Keep an instance's internal steps as ordinary private functions called from that one `@task`, rather than one Airflow task per step - splitting them out would let Airflow schedule a later step of instance 2 before an earlier step of instance 1 finishes, defeating the point. `retries=0` is deliberate here too: a mid-lifecycle failure (say, after `_query` but before `_close_conn`) means a retry would call `_get_db_conn` again on a connection the failed attempt may have already touched - safer to fail the instance and let it be investigated or manually rerun than to retry blind into an unknown partial state.

```python
def _get_db_conn(spec: dict):
    ...

def _query(conn, spec: dict) -> list:
    ...

def _process(rows: list) -> None:
    ...

def _close_conn(conn) -> None:
    ...

@task(
    max_active_tis_per_dag=1,
    retries=0,
    map_index_template="""{{ task.parameters['spec']['date'] }}""",
)
def run_one(spec: dict) -> None:
    conn = _get_db_conn(spec)
    _process(_query(conn, spec))
    _close_conn(conn)

run_one.expand(spec=build_specs())
```

# Branching and gating

- Prefer `@task.short_circuit()` for "should this entire downstream chain run at all" decisions - it returns a bool, not a task_id.
- Reserve `@task.branch` for genuine multi-path routing where the task returns the specific downstream `task_id` to run.
- `ignore_downstream_trigger_rules` (default `True`) controls what a short-circuit's "no" does to everything downstream: `True` force-skips every downstream task regardless of its own `trigger_rule`. `False` only skips the *immediate* downstream tasks and lets Airflow's normal trigger_rule evaluation propagate from there - set `False` whenever a downstream join task uses `trigger_rule="none_failed_min_one_success"` (or similar) and needs to see "skipped", not be force-skipped itself, so it can still run.
- Default join/gate `trigger_rule` after any optional or skippable upstream is `"none_failed_min_one_success"`. Never leave the default `all_success` on a task downstream of a branch or short-circuit when another valid branch may be skipped - `all_success` requires every upstream to have actually run and succeeded, so the join itself gets skipped the moment one branch is skipped, not force-failed.
- Use `Label("condition text")` on a `>>` dependency to document why a path is taken/skipped.

```python
@task.short_circuit(ignore_downstream_trigger_rules=False)
def should_continue() -> bool:
    context = get_current_context()
    return context["params"].get("run_extra_step", False)

@task.branch
def choose_path() -> str:
    context = get_current_context()
    if context["params"].get("skip_step_a"):
        return "step_b"
    return "step_a"

gate = should_continue()
gate >> Label("run_extra_step param is true") >> optional_step()

@task(trigger_rule="none_failed_min_one_success")
def join_after_branch(...) -> None:
    ...
```

# Fail-fast validation

- Raise `AirflowFailException` with a descriptive f-string for "this should never happen" precondition guards - not for expected/recoverable business exceptions.
- Raise `AirflowSkipException` when a task genuinely has nothing to do (e.g. an empty input list, a source with no new data) and that's a normal, expected outcome - not a failure. Prefer this over branching around the task when the "nothing to do" check only applies to one task, not a whole downstream path.
- Project convention, not an Airflow requirement: when classifying a run (e.g. "is this a recovery run triggered by another DAG") based on ambiguous signals, require two independent signals to agree (e.g. a `conf` marker AND a deterministic `run_id` prefix) and document why in the docstring - a single signal can misclassify a run.
- Idempotent-resource-creation pattern, for any task that provisions something external (a cluster, a table, a file): read current state first; if it already exists in a state that means "this task already succeeded", skip creation and return; if it exists in any other unexpected state, fail loud rather than silently overwriting or duplicating. This makes retries safe - a retry after a partial failure doesn't re-create or clobber what the first attempt already made.

```python
@task
def ensure_resource_created(spec: dict) -> None:
    existing = get_resource(spec["name"])
    if existing is not None:
        if existing["status"] not in EXPECTED_TERMINAL_STATES:
            raise AirflowFailException(
                f"Resource '{spec['name']}' already exists in unexpected "
                f"status '{existing['status']}'; refusing to proceed."
            )
        return
    create_resource(spec)
```

# Exception handling

- Default to letting a task throw. An uncaught exception fails the task instance, which triggers Airflow's own retry/alerting machinery (`retries`, `on_failure_callback`) - that machinery exists so individual tasks don't have to reimplement "log it and hope" error handling themselves.
- Don't wrap a task body in a broad `try/except Exception` that logs and swallows the error to keep the task "green" - a swallowed exception hides the failure from retries, from `on_failure_callback` alerting, and from anyone reading the DAG's run history, all at once.
- Only catch a narrow, specifically-typed exception, and only when there's a real decision to make with it - re-raise unless you're doing one of:
  - The idempotent-resource-creation check from "Fail-fast validation" above, where the exception type itself (not just a status check) is what signals "doesn't exist yet".
  - Recording a genuinely expected, non-fatal condition as a result (e.g. one item in a batch hit a known transient error) - and only if that's logged and surfaced in the task's return value/summary, not silently dropped.
- Never catch-log-continue on an exception type you didn't anticipate (bare `except Exception` or `except:`) - if you don't know what it means, you don't know that it's safe to continue past.

```python
logger = logging.getLogger(__name__)

@task
def process_batch(items: list) -> dict:
    skipped = []
    for item in items:
        try:
            handle(item)
        except KnownTransientError as e:
            logger.warning(f"{item}: transient error, recording as skipped: {e}")
            skipped.append(item)
        # anything else propagates and fails the task instance
    return {"skipped": skipped}
```

# Logging

- Log every decision the DAG's own logic makes, not just errors: which branch a gate took and why, which mode a run resolved to, what got selected/skipped and on what basis. A reader should be able to reconstruct "what did this run decide to do" from the logs alone, without reading the code alongside them.
- Log the outcome of each significant step - what succeeded, what failed, what was skipped - especially in a loop over a batch, where per-item success/failure would otherwise be invisible until the whole task's return value.
- Use the module-level `logger = logging.getLogger(__name__)`, not print or the root logger.
- Log before raising, when the exception message alone won't carry enough context (e.g. include the relevant id/state so it's visible even if the traceback gets truncated in a log viewer).

```python
logger = logging.getLogger(__name__)

@task.branch
def choose_path_logged() -> str:
    context = get_current_context()
    decision = "step_b" if context["params"].get("skip_step_a") else "step_a"
    logger.info(f"choose_path_logged: skip_step_a={context['params'].get('skip_step_a')} -> {decision}")
    return decision
```

# Params, config, and constants

- Declare `Param` with the full validation surface available: `type=["string", "null"]` for optional params, `enum=[...]` for closed choices, `pattern=r"..."` for format-constrained strings, `format="date"`, and a `title`.
- Pull static Python/environment configuration into named module-level constants. Do not call `Variable.get()` (or fetch a Connection) at module scope - DAG files are re-parsed repeatedly, so a parse-time call means repeated metadata-DB/secrets-backend hits and slower parsing. Read Airflow Variables inside task runtime code (`Variable.get(...)` inside the task body or via `get_current_context()`), or through templated `{{ var.value.KEY }}` / `{{ var.json.KEY }}` in operator kwargs; parse JSON-shaped variables with `json.loads(...)` at that same point.
- Name magic strings as SCREAMING_SNAKE module constants (e.g. `MODE_BACKUP`, `STATUS_ERROR`) instead of repeating literals.
- Distinguish manual vs. scheduled runs explicitly (e.g. checking `context["dag_run"].run_type` or a dedicated helper) and only honor param overrides on manual runs.

```python
"target_id": Param(
    None,
    type=["null", "string"],
    title="Target identifier",
    pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
),
```

# XCom

- Inside a task body: `get_current_context()["task_instance"].xcom_pull(task_ids="...")` - use this (instead of a plain TaskFlow argument) when a task needs to join/aggregate the XComs of several upstream (often mapped) task instances into one combined result, e.g. `xcom_pull(task_ids="process_item")` inside a `summarize` task that consumes every mapped instance's output at once.
- Inside operator kwargs (e.g. `TriggerDagRunOperator.conf`): the Jinja form, `"{{ ti.xcom_pull(task_ids='plan_run')['run_id'] }}"`.
- `@task(multiple_outputs=True)` when a task's dict return should unpack into multiple named XComs instead of one blob.
- Don't push/pull a value through XCom if it can instead be read or computed directly from `get_current_context()` in the consuming task - e.g. don't have an upstream task return `logical_date` or a `prev_day` derived from it; the downstream task can call `get_current_context()` and compute `prev_day` itself. Threading it through XCom adds a needless dependency edge and an extra serialized copy for something already available for free.
- Same reasoning, different source: config values (a connection id, a constant) belong in an Airflow Variable or module-level constant, read directly by whichever task needs them - not pushed by an earlier task just so a later one can pull it.
- Push scalars or small dicts only - a table name, an id, a count, a status string. Never a full DataFrame or a raw API response; for real payloads, write to storage (S3, a table) and XCom the pointer/path instead.
- Push only what the next task actually consumes - don't carry fields nobody downstream reads just because they were available.
- One XCom, one clear piece of data. If a task's return dict is turning into a general-purpose bag, split it into separate named XComs with `@task(multiple_outputs=True)` instead of one nested blob a reader has to unpack to understand.
- If the same value is passed unchanged through 3+ tasks, that's a sign it belongs in a constant/Variable/context, not a relay chain of XComs.

# TaskGroups

- Use the `@task_group` decorator, not the `task_group=` operator kwarg (which silently ignores the group's `default_args`) and not the raw `TaskGroup(...)` context-manager form.
- Give complex groups a `tooltip` describing their purpose.
- A group owns the dependencies between its own internal tasks - wire them with `>>` inside the `@task_group` function, not from outside after calling it. Only the group's external inputs/outputs (what feeds in, what it returns) should cross the group boundary.

```python
@task_group(tooltip="Fetch and validate one source's data")
def ingest_source(source: str):
    raw = fetch(source)
    validate(raw)
```

# Cross-DAG triggering

`TriggerDagRunOperator` for triggering and blocking on another DAG's run:

```python
trigger_child = TriggerDagRunOperator(
    task_id="trigger_child",
    trigger_dag_id="child_dag",
    trigger_run_id="{{ ti.xcom_pull(task_ids='build_child_run_id') }}",
    logical_date="{{ logical_date }}",
    conf={"source_dag_id": DAG_ID},
    reset_dag_run=True,  # see reset_dag_run policy below
    wait_for_completion=True,
    poke_interval=300,
    allowed_states=["success"],
    failed_states=["failed"],
)
```

Avoid combining `reset_dag_run=True` with `deferrable=True` - known to hang in deferred state on some Airflow versions (apache/airflow#57756). Use `wait_for_completion` with `poke_interval` (as above) instead when `reset_dag_run=True` is needed.

Set `trigger_run_id` deterministically up front (Airflow 3's operator never pushes the child's run id back via XCom) when a downstream task needs to look the child run up later.

`reset_dag_run` decides what happens if that deterministic run id already exists, and the three options are materially different operational policies - pick deliberately, don't leave it implicit in the example:
- `reset_dag_run=True` - clear and re-run the existing run (use for "this trigger should always produce a fresh run for this id").
- `reset_dag_run=False` (default) - fail if the run id already exists (use when a duplicate trigger for the same id is a bug you want surfaced, not silently handled).
- Reattach instead of triggering - check for an existing run first and only call `TriggerDagRunOperator` if none exists, when the desired behavior is "join the existing run rather than reset or fail".

# Sensors

Prefer a purpose-built deferrable operator/sensor when one exists for the thing being waited on and the deployment supports deferral (a triggerer is running) - it frees the worker slot entirely instead of just rescheduling it. When writing a custom `@task.sensor`, prefer `mode="reschedule"` over the bare/default poke mode for any wait that shouldn't occupy a worker slot continuously: `@task.sensor(poke_interval=60, timeout=..., mode="reschedule")`. Express `timeout` via a named constant, not a magic number, and keep `poke_interval` conservative (roughly `>= 60s`) in reschedule mode - too-frequent rescheduling puts pressure on the scheduler.

# Documentation

- Set a short `description` plus a module-level `DAG_DOC` constant (markdown, including an ASCII flow diagram for anything with more than a couple of branches) passed to `doc_md`. Keep the two separate: `description` is the one-liner shown in the DAG list, `doc_md` is the full write-up.

````python
DAG_DOC = """
### my_dag

One-paragraph purpose statement.

## Task flow

```text
START
  |
  v
gate -> task_a -> task_b
```
"""
````

# .partial() + .expand(): passing extra params to a mapped task

A mapped task's signature often needs more than just the expanded element - `.expand()` alone only supplies the varying value. `.partial(**fixed_kwargs)` supplies the rest: every mapped instance gets the same `fixed_kwargs` plus its own value for whatever `.expand()` maps.

```python
@task(map_index_template="""{{ task.parameters['table'] }}""")
def process_table(table: str, mode: str) -> None:
    ...

process_table.partial(mode="incremental").expand(table=["orders", "users", "payments"])
```

Pre-filter/validate the input list before expanding - mapping over an unfiltered or unbounded list creates one task instance per element, so a bad or huge input list becomes an uncontrolled fan-out.

# Debugging via the REST API

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

# Docstrings

For any non-trivial task, the docstring documents its I/O contract, not just what it does - a one-line summary, then paragraph(s) covering:
- What it receives and consumes (which args, and if reading upstream XComs, which task_ids/keys exactly - "consumes exactly X" is more useful than describing the whole upstream object).
- What it returns (the exact shape - which keys, not just "a dict").
- When it raises, and why (which precondition failures propagate as which exception type).
- Whether it has side effects (writes, mutates external state) or is read-only.

This matters more here than in typical Python because a task's real interface is implicit - its XCom inputs/outputs aren't visible in the function signature the way normal Python args are, so the docstring is often the only place that contract is written down.

```python
@task
def fetch_orders(since: str) -> dict:
    """Fetch orders placed since `since` from the orders API.

    Receives `since` (an ISO date string). Returns a dict with exactly
    `orders` (list of raw order dicts). Raises `AirflowFailException` if
    the API returns a non-2xx response. Read-only.
    """
    ...

@task
def dedupe_orders(fetch_result: dict) -> dict:
    """Drop orders already present in the target table.

    Receives `fetch_result` and consumes exactly its `orders` key. Returns
    a dict with exactly `new_orders` (list). Raises nothing expected - a
    query failure propagates. Read-only.
    """
    ...

@task
def load_orders(dedupe_result: dict) -> None:
    """Insert new orders into the target table.

    Receives `dedupe_result` and consumes exactly its `new_orders` key.
    Returns None. Raises `AirflowSkipException` if `new_orders` is empty.
    Uses an upsert (insert-or-ignore on order id) so a retry after a
    partial failure re-inserts safely instead of duplicating rows.
    """
    ...

fetched = fetch_orders(since="{{ ds }}")
load_orders(dedupe_orders(fetched))
```

# Personal conventions

- Use `pendulum` throughout for all date/time handling (`pendulum.datetime(...)`, `pendulum.duration(...)`, `pendulum.now("UTC")`, `.to_datetime_string()`) rather than the stdlib `datetime`/`timedelta`.
- Type-hint every task's parameters and return value using the stdlib `typing` module (`typing.List`, `typing.Dict`, `typing.Optional`, `typing.Any`) rather than bare built-in generics.
- Unless code is repeated, prefer inline logic inside the task definition over extracting a function - see "Serializing mapped instances" above for the one exception.
