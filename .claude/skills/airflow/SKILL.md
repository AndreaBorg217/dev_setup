---
name: airflow
description: Manages Apache Airflow DAGs, tasks, operators, sensors and XComs. Use when reading, changing or operating Airflow workflows; not for generic Python orchestration.
when_to_use: "DAG, task, operator, sensor, XCom, retry behaviour, task mapping, branching, setup/teardown, params, docstrings, REST API, task state, logs, dry-run, clear task instances, retry task instances, delete runs, pause a DAG"
---

# Airflow

Load the `coding` skill as well for Airflow source or test work.

Choose only the detail needed for this task:

- Authoring, review, DAG structure, retry behaviour, task mapping, branching,
  setup/teardown, XCom, params, documentation, and docstrings: read
  [references/authoring.md](references/authoring.md).
- Live DAG operations, REST API calls, task state, logs, and XCom inspection:
  read [reference.md](reference.md).
- Copyable implementation patterns: read only the matching section of
  [examples.md](examples.md), after the authoring rule routes you there.

Never perform a non-dry-run mutation such as clearing or retrying task
instances, deleting runs, or pausing a DAG without explicit approval.
