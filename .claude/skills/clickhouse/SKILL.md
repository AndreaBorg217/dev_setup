---
name: clickhouse
description: Use when writing or debugging ClickHouse SQL, tuning or diagnosing ClickHouse backup/restore performance, or designing/operating a ClickHouse Kafka-engine ingestion pipeline.
when_to_use: "ClickHouse, SELECT, EXPLAIN, ORDER BY, PARTITION BY, sorting_key, FINAL, argMax, ReplacingMergeTree, MergeTree, materialized view, ENGINE = Kafka, kafka_broker_list, kafka_topic_list, kafka_group_name, kafka_skip_broken_messages, kafka_handle_error_mode, system.kafka_consumers, system.metric_log, system.parts, system.detached_parts, detached parts, frozen parts, OPTIMIZE FINAL, fragmented partitions, consumer lag, dictGet, duplicate rows, slow query, granules, backup restore performance, restore plan eligibility"
---

# ClickHouse

Load this skill once before writing or debugging a ClickHouse query, tuning
or diagnosing a backup/restore job, or designing/operating a Kafka-engine
pipeline. Keep its instructions active for the rest of that task.

## Query efficiently

Read [references/query-patterns.md](references/query-patterns.md) before
writing a query against a large table or diagnosing a slow one - it covers
checking whether a query is actually pruning, deduplicating a
`ReplacingMergeTree` correctly (`FINAL` vs manual `argMax`, and when to reach
for which), `dictGet` dimension lookups, and access-control introspection
(grants, quotas, row policies).

## Backup and restore performance

Read [references/backup-restore.md](references/backup-restore.md) before
tuning or diagnosing a slow backup/restore job - it covers monitoring an
in-progress `BACKUP`/`RESTORE` from `system.backups`, sanity-checking restore
completeness by counting landed objects, checking which storage tier
restored data actually landed on, querying your own backup run-history
table, and measuring the actual bottleneck with `system.metric_log` before
changing any concurrency setting.

## The Kafka table engine

Read [references/kafka-engine.md](references/kafka-engine.md) before
creating or debugging an `ENGINE = Kafka` table - it covers the standard
ingestion architecture, the settings worth deliberately tuning and why,
extracting one clause out of a large table/MV DDL instead of reading it
whole, checking for shared consumer thread-pool exhaustion, reading full
exception history instead of just the latest exception, reconciling row
counts against the source system, and rules for avoiding failure modes this
engine is prone to: a poison-pill message silently stalling a consumer, an
orphaned consumer with nothing draining it, cluster nodes with an
inconsistent Kafka table definition, and safe cutover ordering.

## Parts maintenance

Read [references/parts-maintenance.md](references/parts-maintenance.md)
before triaging detached parts, cleaning up frozen parts, or deciding
whether a table needs `OPTIMIZE ... FINAL` - it covers reading the detach
reason from a part's prefix, fetching a part from a healthy replica,
checking whether a replica has actually caught up, finding fragmented
partitions worth optimizing, and detecting which `ReplacingMergeTree`
partitions genuinely still hold duplicates rather than assuming from a time
window.

## Keep it generic

Do not write real broker addresses, topic names, table names, database names,
or schema-registry URLs into this skill or its reference files. Use
placeholders (`$KAFKA_BROKER_LIST`, `$TOPIC`, `$TABLE`, `$CONSUMER_GROUP`) in
any example added here.
