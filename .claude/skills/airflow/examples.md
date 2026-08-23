# Examples

Full runnable code for each pattern in [SKILL.md](SKILL.md). Section headers match SKILL.md so the links resolve.

## Serializing mapped instances

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

## Branching and gating

```python
@task.branch
def choose_processing_path() -> str:
    context = get_current_context()
    decision = "fast_path" if context["params"].get("small_batch") else "full_path"
    logger.info(f"choose_processing_path: small_batch={context['params'].get('small_batch')} -> {decision}")
    return decision

@task(trigger_rule="none_failed_min_one_success")
def join_after_branch() -> None:
    context = get_current_context()
    result = context["task_instance"].xcom_pull(task_ids=["fast_path", "full_path"])
    ...

choose_processing_path() >> [fast_path(), full_path()] >> join_after_branch()
```

## Fail-fast validation

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

## Setup and teardown

Unconditional cleanup - pair `@task.setup` with `@task.teardown`:

```python
@task.setup
def create_temp_table() -> str:
    context = get_current_context()
    table_name = f"tmp_{context['ts_nodash']}"
    ...
    return table_name

@task.teardown
def drop_temp_table(table_name: str) -> None:
    ...

table_name = create_temp_table()
work = do_work(table_name)
table_name >> work >> drop_temp_table(table_name).as_teardown(setups=table_name)
```

Conditional cleanup - route with `@task.branch` instead, never a conditional `@task.teardown`:

```python
@task.branch
def choose_teardown_path() -> str:
    context = get_current_context()
    is_manual = context["dag_run"].run_type == DagRunType.MANUAL
    verification_passed = context["ti"].xcom_pull(task_ids="verify")
    decision = "drop_temp_table" if (not is_manual and verification_passed) else "preserve_temp_table"
    logger.info(
        f"choose_teardown_path: is_manual={is_manual}, "
        f"verification_passed={verification_passed} -> {decision}"
    )
    return decision

@task
def drop_temp_table(table_name: str) -> None:
    drop_table(table_name)

@task
def preserve_temp_table(table_name: str) -> None:
    logger.info(f"preserve_temp_table: leaving {table_name} in place for inspection")

choose_teardown_path() >> [drop_temp_table(table_name), preserve_temp_table(table_name)]
```

## Exception handling

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

## Params, config, and constants

```python
"target_id": Param(
    None,
    type=["null", "string"],
    title="Target identifier",
    pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
),
```

## TaskGroups

```python
@task_group(tooltip="Fetch and validate one source's data")
def ingest_source(source: str):
    raw = fetch(source)
    validate(raw)
```

## Cross-DAG triggering

```python
trigger_child = TriggerDagRunOperator(
    task_id="trigger_child",
    trigger_dag_id="child_dag",
    trigger_run_id="{{ ti.xcom_pull(task_ids='build_child_run_id') }}",
    logical_date="{{ logical_date }}",
    conf={"source_dag_id": DAG_ID},
    reset_dag_run=True,  # see reset_dag_run policy in SKILL.md
    wait_for_completion=True,
    poke_interval=300,
    allowed_states=["success"],
    failed_states=["failed"],
)
```

## Documentation

```python
with DAG(
    dag_id="orders_pipeline",
    description="Fetches, deduplicates, and loads new orders.",
    doc_md="""
### Orders Pipeline

Fetches orders from the Orders API, removes orders already present in the target table, and loads the remaining orders.

## Running manually

The DAG can be triggered from the Airflow UI.

Supported params:

- `since`: ISO date used as the lower bound when fetching orders.

## Side effects

- Inserts new rows into the target orders table.

## Dependencies

- Airflow connection: `orders_api` with API credentials.
- Airflow connection: `orders_db` with Postgres credentials.

## Failure modes

- Fails if the Orders API returns a non-2xx response.
- Database query and insert failures propagate.
- The load task is skipped when there are no new orders.
- Inserts are idempotent on `order_id`, so retries do not create duplicate rows.
""",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:
    ...
"""

## .partial() + .expand()

```python
@task(map_index_template="""{{ task.parameters['table'] }}""")
def process_table(table: str, mode: str) -> None:
    ...

process_table.partial(mode="incremental").expand(table=["orders", "users", "payments"])
```

## Docstrings

```python
@task
def fetch_orders(since: str) -> dict:
    """Fetches orders placed since the given date from the orders API
    Params:
    - since: str -> ISO date string
    Returns:
    - orders: List[Dict] -> raw orders returned by the API
    Throws:
    - AirflowFailException if the API returns a non-2xx response
    """
    ...

@task
def dedupe_orders(fetch_result: dict) -> dict:
    """Drops orders already present in the target table
    Params:
    - fetch_result: Dict -> consumes only `orders`, a list of raw order dicts
    Returns:
    - new_orders: List[Dict] -> orders not already present in the target table
    Throws:
    - Query failures propagate
    """
    ...

@task
def load_orders(dedupe_result: dict) -> None:
    """Inserts new orders into the target table
    Params:
    - dedupe_result: Dict -> consumes only `new_orders`, a list of orders to insert
    Returns:
    - None
    Throws:
    - AirflowSkipException if `new_orders` is empty

    Uses an upsert (insert-or-ignore on order id), so retries after a partial
    failure can safely re-insert orders without creating duplicates.
    """
    ...

fetched = fetch_orders(since="{{ ds }}")
load_orders(dedupe_orders(fetched))
```
