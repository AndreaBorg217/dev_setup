---
name: airflow
description: Use when authoring, reviewing, debugging, testing, or operating Apache Airflow DAGs, tasks, sensors, operators, scheduling, XComs, or task mapping.
---

This file covers principles and decision rules. Full runnable code for every pattern below lives in [examples.md](examples.md); operational/debugging reference lives in [reference.md](reference.md).

# Authoring principles

- A task should be a small idempotent piece of work that can be retried without side effects. Before looping over a list inside a task, consider `.expand()` instead - see "Serializing mapped instances" below for the case where instances must run strictly one after another.
- Any `@task` used with `.expand()` needs `map_index_template` set, e.g. `map_index_template="""{{ task.parameters['date'] }}"""`, so each mapped instance shows a readable name in the UI instead of a bare index.
- Always consider side effects of a retry -> alerts, writes to a sink, etc.
- Use `max_active_tis_per_dag` to cap concurrent instances of one mapped task - across active runs of the DAG, not just within one run. See "Serializing mapped instances" for the `1`-instance case.
- Use DAG-level `max_active_tasks` to cap concurrent task instances within a single DAG run. It does not limit concurrency across separate runs of the same DAG or across DAGs - use an Airflow Pool for that.
- Use `get_current_context` inside the task body instead of passing context variables (e.g. `logical_date`) as a parameter. A task should only receive XComs it cannot compute itself, and only the ones it needs.
- Prefer TaskFlow decorators (`@task`, `@task.sensor`, `@task.branch`, `@task.short_circuit`, `@task_group`) for custom Python logic; use purpose-built operators/sensors when one already implements the required external-system behavior (e.g. `TriggerDagRunOperator`) rather than reimplementing it as a `@task`. Define the DAG with `with DAG(...)` syntax.
- Default the `schedule` parameter to `CronTriggerTimetable`.
- Default a DAG to `max_active_runs=1` unless it's specifically designed for multiple runs in flight (e.g. independent per-partition backfills). Without this cap, a slow run plus normal schedule cadence can pile up overlapping runs that race each other.

See "Personal conventions" below for team style choices (inline-vs-function, pendulum, `typing`, etc) that are not Airflow requirements.

# Retries and backoff

- Task-level: `retries`, `retry_delay` (base `timedelta`), `retry_exponential_backoff` (bool), `max_retry_delay` (cap). Set sane defaults in `default_args`, override per-task only where needed - see "Serializing mapped instances" for the `retries=0` case.
- With `retry_exponential_backoff=True`, wait grows roughly exponentially off `retry_delay`, deterministic jitter is added, and the result is capped at `max_retry_delay`. The exact arithmetic has changed across Airflow versions - check `next_retry_datetime` in the installed Airflow's `taskinstance.py` if the precise formula matters, rather than trusting a hardcoded formula.
- Don't hand-roll a sleep/backoff loop inside a task body to work around a flaky dependency - use these operator-level knobs so retry behavior stays visible in the UI.

# Serializing mapped instances

`max_active_tis_per_dag=1` on a mapped (`.expand()`-ed) task holds each instance for its full runtime - the next instance cannot begin until the current one ends. Reach for this when instances must run strictly one after another, not just capped in number. Neither `TaskGroup` nor `@task_group` has an equivalent throttle for its own expanded children, so this task-level setting is the only lever.

Keep an instance's internal steps as ordinary private functions called from that one `@task`, rather than one Airflow task per step - splitting them out would let Airflow schedule a later step of instance 2 before an earlier step of instance 1 finishes, defeating the point. `retries=0` is deliberate too: a mid-lifecycle failure means a retry could touch a resource (e.g. a DB connection) the failed attempt already touched - safer to fail the instance and let it be investigated or manually rerun than retry blind into a partial state.

See [examples.md#serializing-mapped-instances](examples.md#serializing-mapped-instances) for the pattern.

# Branching and gating

The two constructs have different jobs, and mixing them up (or wiring a `trigger_rule` around the seam) is where a DAG stops reading top-to-bottom as it runs.

- **`@task.short_circuit()` means "halt the DAG here, full stop."** Leave `ignore_downstream_trigger_rules` at its default (`True`) always. If it returns `False`, everything downstream is skipped, unconditionally. Don't set `ignore_downstream_trigger_rules=False`, and don't put a `trigger_rule="none_failed_min_one_success"` join downstream of a short-circuit hoping it survives the skip - that trades a readable DAG for trigger-rule plumbing invisible from where the decision was made. Reserve short-circuit for genuine abort conditions: no new data to process, a required precondition entirely absent, a param that says "don't run today."
- **If the DAG should keep running but through one path rather than another, that's `@task.branch`'s job, not a short-circuit's.** A branch task returns the specific downstream `task_id`(s) to run next, so the decision and its consequence are both visible in the return value.
- **Fan-in after a branch is the one place `trigger_rule="none_failed_min_one_success"` is the standard, expected pattern, not something to avoid.** `@task.branch` marks every unchosen path's tasks as skipped - that's how branching works - so a join task those paths funnel back into needs this trigger*rule, or the default `all_success` would leave it permanently skipped. This differs from the short-circuit anti-pattern above: there, the trigger_rule was making a task survive a \_halt-the-DAG* decision it was never meant to survive; here, it's acknowledging the normal outcome of "exactly one of these paths runs."
- If the join needs to combine what different branches actually produced (not just synchronize), pull the branch-specific XComs by `task_ids` inside the join task's body (see "XCom" below) rather than routing a value through every branch unconditionally.
- Use `Label("condition text")` on a `>>` dependency to document why a path is taken/skipped.

See [examples.md#branching-and-gating](examples.md#branching-and-gating).

# Fail-fast validation

- Raise `AirflowFailException` with a descriptive f-string for "this should never happen" precondition guards - not expected/recoverable business exceptions.
- Raise `AirflowSkipException` when a task genuinely has nothing to do (empty input list, no new data) and that's a normal, expected outcome. Prefer this over branching around the task when the "nothing to do" check only applies to one task.
- Project convention, not an Airflow requirement: when classifying a run on ambiguous signals (e.g. "is this a recovery run"), require two independent signals to agree and document why in the docstring - a single signal can misclassify a run.
- Idempotent-resource-creation pattern, for any task that provisions something external: read current state first; if it already exists in a "this task already succeeded" state, skip and return; if it exists in any other unexpected state, fail loud rather than silently overwriting. This makes retries safe.

See [examples.md#fail-fast-validation](examples.md#fail-fast-validation).

# Setup and teardown

The deciding question is whether cleanup must run **unconditionally**, no matter what happened upstream. That's the entire value `@task.teardown` provides, and it's also its limit.

- **Use `@task.teardown` only when the resource must always be cleaned up, full stop.** Pair a `@task.setup` with a `@task.teardown` (`.as_setup()` / `.as_teardown(setups=...)`) for a resource - a temp table, a staging path, a scratch cluster - that has no legitimate reason to survive the run, regardless of whether the work between them succeeded, failed, or was skipped. Airflow runs the teardown whenever its paired setup ran, and by default its own outcome doesn't count toward the DAG run's success/failure (`on_failure_fail_dagrun=True` if it should). Don't reach for a manual try/finally or a `trigger_rule="all_done"` cleanup task to get this behavior - `@task.teardown` is built for exactly this.
- **The moment cleanup becomes conditional on anything, don't use `@task.teardown` at all - route it with a plain `@task.branch` instead.** If teardown should be withheld under some condition (a verification check failed and the resource should be preserved for inspection, the DAG was triggered manually and the resource is meant to be reused, etc), that decision belongs in an ordinary branch task naming which downstream `task_id` to run - not inside a `@task.teardown`, and not behind a short-circuit (see "Branching and gating": short-circuit halts the whole DAG, it isn't a per-resource conditional). Baking a condition into a teardown (e.g. `AirflowSkipException` from inside it) fights the construct: a teardown that sometimes doesn't run is really just a regular task wearing a teardown decorator - a branch says the same thing more clearly.

See [examples.md#setup-and-teardown](examples.md#setup-and-teardown).

# Exception handling

- Default to letting a task throw. An uncaught exception fails the task instance, which triggers Airflow's own retry/alerting machinery (`retries`, `on_failure_callback`) - that machinery exists so tasks don't reimplement "log it and hope" themselves.
- Don't wrap a task body in a broad `try/except Exception` that logs and swallows the error to keep it "green" - that hides the failure from retries, alerting, and run history all at once.
- Only catch a narrow, specifically-typed exception, and only when there's a real decision to make with it - re-raise unless you're doing one of:
    - The idempotent-resource-creation check from "Fail-fast validation," where the exception type itself is what signals "doesn't exist yet."
    - Recording a genuinely expected, non-fatal condition as a result (e.g. one item in a batch hit a known transient error) - only if it's logged and surfaced in the return value, not silently dropped.
- Never catch-log-continue on an exception type you didn't anticipate (bare `except Exception` or `except:`) - if you don't know what it means, you don't know it's safe to continue past.

See [examples.md#exception-handling](examples.md#exception-handling).

# Logging

- Log every decision the DAG's own logic makes, not just errors: which branch a gate took and why, which mode a run resolved to, what got selected/skipped and on what basis. A reader should be able to reconstruct "what did this run decide to do" from the logs alone.
- Log the outcome of each significant step - what succeeded, what failed, what was skipped - especially in a batch loop, where per-item results would otherwise be invisible until the whole task's return value.
- Use the module-level `logger = logging.getLogger(__name__)`, not print or the root logger.
- Log before raising, when the exception message alone won't carry enough context.

The branching, fail-fast, and setup/teardown examples in [examples.md](examples.md) all demonstrate this pattern in context.

# Params, config, and constants

- Declare `Param` with the full validation surface available: `type=["string", "null"]` for optional params, `enum=[...]` for closed choices, `pattern=r"..."` for format-constrained strings, `format="date"`, and a `title`.
- Pull static config into named module-level constants. Don't call `Variable.get()` (or fetch a Connection) at module scope - DAG files are re-parsed repeatedly, so a parse-time call means repeated metadata-DB/secrets-backend hits. Read Variables inside task runtime code, or via templated `{{ var.value.KEY }}` / `{{ var.json.KEY }}` in operator kwargs.
- Name magic strings as SCREAMING_SNAKE module constants instead of repeating literals.
- Distinguish manual vs. scheduled runs explicitly (`context["dag_run"].run_type`) and only honor param overrides on manual runs.

See [examples.md#params-config-and-constants](examples.md#params-config-and-constants).

# XCom

- Inside a task body: `get_current_context()["task_instance"].xcom_pull(task_ids="...")` - use this (instead of a plain TaskFlow argument) when a task needs to join/aggregate the XComs of several upstream (often mapped or branched) task instances into one result.
- Inside operator kwargs (e.g. `TriggerDagRunOperator.conf`): the Jinja form, `"{{ ti.xcom_pull(task_ids='plan_run')['run_id'] }}"`.
- `@task(multiple_outputs=True)` when a task's dict return should unpack into multiple named XComs instead of one blob.
- Don't push/pull a value through XCom if it can instead be read or computed directly from `get_current_context()` in the consumer - threading it through XCom adds a needless dependency edge and a serialized copy for something already available for free.
- Same reasoning, different source: config values (a connection id, a constant) belong in a Variable or module-level constant, read directly by whichever task needs them - not pushed by an earlier task just so a later one can pull it.
- Push scalars or small dicts only. Never a full DataFrame or raw API response - for real payloads, write to storage and XCom the pointer/path instead.
- Push only what the next task actually consumes.
- One XCom, one clear piece of data. If a task's return dict is turning into a general-purpose bag, split it into separate named XComs with `multiple_outputs=True`.
- If the same value is passed unchanged through 3+ tasks, it belongs in a constant/Variable/context, not a relay chain of XComs.

# TaskGroups

- Use the `@task_group` decorator, not the `task_group=` operator kwarg (silently ignores the group's `default_args`) and not the raw `TaskGroup(...)` context-manager form.
- Give complex groups a `tooltip` describing their purpose.
- A group owns the dependencies between its own internal tasks - wire them with `>>` inside the `@task_group` function. Only the group's external inputs/outputs should cross the group boundary.

See [examples.md#taskgroups](examples.md#taskgroups).

# Cross-DAG triggering

`TriggerDagRunOperator` triggers and blocks on another DAG's run. Avoid combining `reset_dag_run=True` with `deferrable=True` - known to hang in deferred state on some Airflow versions (apache/airflow#57756); use `wait_for_completion` with `poke_interval` instead. Set `trigger_run_id` deterministically up front (Airflow 3 never pushes the child's run id back via XCom) when a downstream task needs to look the child run up later.

`reset_dag_run` decides what happens if that deterministic run id already exists - three materially different operational policies, pick deliberately:

- `reset_dag_run=True` - clear and re-run the existing run ("this trigger should always produce a fresh run for this id").
- `reset_dag_run=False` (default) - fail if the run id already exists (a duplicate trigger is a bug you want surfaced).
- Reattach instead of triggering - check for an existing run first and only call `TriggerDagRunOperator` if none exists ("join the existing run rather than reset or fail").

See [examples.md#cross-dag-triggering](examples.md#cross-dag-triggering).

# Sensors

Prefer a purpose-built deferrable operator/sensor when one exists and the deployment supports deferral (a triggerer running) - it frees the worker slot entirely instead of just rescheduling it. When writing a custom `@task.sensor`, prefer `mode="reschedule"` over the default poke mode for any wait that shouldn't occupy a worker slot continuously: `@task.sensor(poke_interval=60, timeout=..., mode="reschedule")`. Express `timeout` via a named constant, and keep `poke_interval` conservative (roughly `>= 60s`) in reschedule mode - too-frequent rescheduling puts pressure on the scheduler.

# Documentation

Set a short `description` plus a `doc_md` containing the full DAG documentation.

Keep the two separate:

- `description` is the one-line summary shown in the Airflow DAG list.
- `doc_md` contains the operational documentation for the DAG.

`doc_md` should document, where applicable:

- **Purpose** — what the DAG does and why it exists.
- **How to run it** — supported Airflow params, expected values, and any relevant manual-trigger behavior.
- **Side effects** — tables, files, APIs, messages, or other external state the DAG creates or modifies.
- **Dependencies** — required Airflow connections, variables, secrets/keys, external services, datasets, or upstream DAGs.
- **Known failure modes** — expected reasons the DAG may fail or skip work, and any important retry/idempotency behavior.

See [examples.md#documentation](examples.md#documentation) for a full DAG with all these sections.

# .partial() + .expand(): passing extra params to a mapped task

A mapped task's signature often needs more than the expanded element - `.expand()` alone only supplies the varying value. `.partial(**fixed_kwargs)` supplies the rest: every mapped instance gets the same `fixed_kwargs` plus its own value for whatever `.expand()` maps. Pre-filter/validate the input list before expanding - mapping over an unfiltered or unbounded list creates one task instance per element, so a bad or huge input list becomes an uncontrolled fan-out.

See [examples.md#partial--expand](examples.md#partial--expand).

# Debugging via the REST API

Resolve credentials from a password manager - never hardcode them, never prompt the user to paste them. Airflow 3 auth is JWT via `POST /auth/token`, `/api/v1` is gone (`/api/v2`). Full auth flow and curl workflows (trigger a run, clear/retry a task instance, fetch logs, fetch an XCom) are in [reference.md](reference.md).

**Guardrails: clearing/retrying task instances, deleting runs, and pausing DAGs are destructive - always confirm with the user before a non-dry-run/mutating call.**

# Docstrings

For any non-trivial task, the docstring documents its I/O contract, not just what it does - a one-line summary, what it receives and consumes, what it returns, when it raises, and why; whether it has side effects or is read-only.

```python
@task
def enrich_orders(orders: List[Dict], users: Dict) -> dict:
    """Enriches orders with user data
    Params:
    - orders: List[Dict]
    - users: Dict -> for each user we consume only user_id, rest is passed because it is needed in return
    Returns:
    - enriched_order: List[Dict] -> orders joined with users on user_id
    Throws:
    - AirflowFailException if order has user_id not found in users
    """
    ...
```

See [examples.md#docstrings](examples.md#docstrings) for a full multi-task chain showing how these contracts connect across tasks.

# Personal conventions

- Use `pendulum` throughout for all date/time handling (`pendulum.datetime(...)`, `pendulum.duration(...)`, `pendulum.now("UTC")`, `.to_datetime_string()`) rather than the stdlib `datetime`/`timedelta`.
- Type-hint every task's parameters and return value using the stdlib `typing` module rather than bare built-in generics.
- Unless code is repeated, prefer inline logic inside the task definition over extracting a function - see "Serializing mapped instances" for the one exception.
