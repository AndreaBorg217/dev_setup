# Kafka table engine reference

## The standard architecture

The `Kafka` engine is a consumer, not storage - it re-reads from its
consumer-group offset on every `SELECT` and does not persist rows itself.
Build the pipeline in four layers:

```
ENGINE = Kafka table (raw consumer, typed as closely to the wire format
    as practical - e.g. leave Avro fields as String where casting on
    ingest is risky)
  -> materialized view ("draining MV") that SELECTs from the Kafka table,
     casts/transforms fields, and INSERTs INTO the storage table
  -> storage table, typically ReplicatedReplacingMergeTree (dedup on
     merge, keyed by the source system's primary key + a version column)
  -> a FINAL-wrapping view (commonly prefixed v_) that downstream
     queries and dashboards actually read from
```

Never query the `Kafka`-engine table directly with a `SELECT` outside its
draining MV - each read consumes and discards those messages for whichever
process ran the query, stealing them from the real consumer.

## Settings worth deliberately tuning

```sql
CREATE TABLE $DATABASE.$TABLE
(
    ...
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = '$KAFKA_BROKER_LIST',
    kafka_topic_list = '$TOPIC',
    kafka_group_name = '$CONSUMER_GROUP',
    kafka_format = 'AvroConfluent',
    format_avro_schema_registry_url = '$SCHEMA_REGISTRY_URL',
    kafka_num_consumers = 1,
    kafka_skip_broken_messages = 0,
    kafka_handle_error_mode = 'default',
    kafka_poll_timeout_ms = 2000,
    kafka_poll_max_batch_size = 65409,
    kafka_flush_interval_ms = 30000,
    kafka_thread_per_consumer = 0
```

- **`kafka_num_consumers`** and **`kafka_thread_per_consumer`** - tune
  together. Raising `kafka_num_consumers` parallelizes across partitions on
  one node, but `kafka_thread_per_consumer` controls whether those consumers
  share one flush thread or get one each - changing only one of the two
  rarely gives the expected result.
- **`kafka_flush_interval_ms`** - lower it to reduce end-to-end ingestion
  latency; raising it produces fewer, larger inserts (fewer parts to merge
  later). This is a latency/part-count tradeoff to make deliberately, not a
  default to leave untouched when latency requirements change.
- **`kafka_poll_max_batch_size`** / **`kafka_poll_timeout_ms`** - bound how
  much a single poll can pull and how long it waits; tune alongside
  `kafka_flush_interval_ms`, not in isolation.

## Pattern: orphaned-consumer detection

A `Kafka`-engine table with no materialized view draining it holds a live
consumer group while its data goes nowhere useful. Cross-reference
`system.tables` for any `ENGINE = Kafka` table that no MV's `FROM` clause
references, and flag it - this is cheap to check and easy to forget after a
table is decommissioned informally:

```sql
SELECT database, name, dependencies_table
FROM system.tables
WHERE engine = 'Kafka'
```

An empty `dependencies_table` means nothing reads from this Kafka table -
it's consuming and discarding messages for no one.

## Pattern: pull one clause out of a Kafka table or MV's DDL instead of dumping it whole

`create_table_query` on a real pipeline table is often too long to read
usefully in one go - especially for a materialized view with a wide
`SELECT`. Extract just the piece under investigation rather than reading the
full string:

```sql
-- the MV's write target
SELECT name, extract(create_table_query, 'TO [`a-zA-Z0-9_\.]+') AS to_clause
FROM system.tables
WHERE database = '$DATABASE' AND name = '$MV_NAME'

-- every join the MV performs
SELECT arrayJoin(extractAll(create_table_query, '(?i)(LEFT JOIN|INNER JOIN|JOIN)[^\(]{0,120}')) AS join_snippet
FROM system.tables
WHERE database = '$DATABASE' AND name = '$MV_NAME'

-- the Kafka table's own SETTINGS block
SELECT extract(create_table_query, 'SETTINGS.*$') AS settings_clause
FROM system.tables
WHERE database = '$DATABASE' AND name = '$KAFKA_TABLE'

-- the ~150 chars of context around a specific column reference
SELECT substring(create_table_query, greatest(position(create_table_query, '$COLUMN_NAME') - 150, 1), 400) AS context
FROM system.tables
WHERE database = '$DATABASE' AND name = '$TABLE'
```

`extract`/`extractAll` for a single labeled clause, `substring` with
`position()` for surrounding context around a known token - both are cheaper
and more readable than eyeballing a multi-hundred-line DDL string.

## Checking for Kafka consumer thread pool exhaustion

ClickHouse services all `Kafka`-engine tables' consumers from one shared
background pool, not one pool per table. A busy pipeline can starve others
on the same server. Compare how many consumers are actually assigned against
the pool size the server is configured for:

```sql
SELECT hostName() AS host, metric, value
FROM clusterAllReplicas('$CLUSTER', system.metrics)
WHERE metric IN ('BackgroundMessageBrokerSchedulePoolTask',
                  'BackgroundMessageBrokerSchedulePoolSize',
                  'KafkaConsumers', 'KafkaConsumersInUse', 'KafkaAssignedPartitions')
ORDER BY host, metric
```

```sql
SELECT hostName() AS host, name, value, changed
FROM clusterAllReplicas('$CLUSTER', system.server_settings)
WHERE name ILIKE '%background_message_broker%' OR name ILIKE '%background_pool_size%'
```

`KafkaConsumersInUse` approaching `BackgroundMessageBrokerSchedulePoolSize`
means the shared pool is saturated - new or existing Kafka tables on that
server will queue for scheduling rather than poll promptly, which looks like
lag but isn't caused by the topic or the consumer group at all. The fix is
raising the pool size setting, not tuning any individual table's Kafka
settings.

## Checking for Kafka-related errors and event counters

Two cheap, generic checks before diving into any one table's specifics:

```sql
-- recent kafka-tagged errors/warnings across the whole server, not just one table
SELECT event_time, level, message
FROM system.text_log
WHERE event_time BETWEEN $START AND $END
  AND message ILIKE '%kafka%'
  AND level IN ('Error', 'Warning')
ORDER BY event_time
LIMIT 30

-- cumulative kafka-related event counters since server start
SELECT event, value FROM system.events WHERE event ILIKE '%kafka%'
```

`system.events` counters are since-startup cumulative, not a rate - diff two
snapshots taken a known interval apart to get a rate, or use
`system.metric_log` (see the backup-restore reference) for a windowed view.


## Monitoring consumer lag and health

```sql
SELECT
    hostName() AS host,
    database,
    table,
    consumer_id,
    assignments.topic,
    assignments.partition_id,
    num_messages_read,
    last_commit_time,
    last_exception_time,
    last_exception
FROM clusterAllReplicas('$CLUSTER', system.kafka_consumers)
WHERE database = '$DATABASE' AND table = '$TABLE'
ORDER BY host
```

Read `last_commit_time` and `last_exception` together, not `num_messages_read`
alone - a climbing `num_messages_read` with a stale `last_commit_time` is the
poison-pill signature above, not a healthy consumer.

## See the full exception history, not just the latest one

`system.kafka_consumers.exceptions.time`/`exceptions.text` are parallel
arrays of recent exception history per consumer, not just the last one.
`ARRAY JOIN` explodes them into rows so a burst of transient errors is
visible as a timeline, not collapsed into a single latest value:

```sql
SELECT hostName() AS host, exception_time, exception_text
FROM clusterAllReplicas('$CLUSTER', system.kafka_consumers)
ARRAY JOIN `exceptions.time` AS exception_time, `exceptions.text` AS exception_text
WHERE database = '$DATABASE' AND table LIKE '$TABLE_PATTERN'
ORDER BY exception_time DESC
LIMIT 50;
```

A single isolated exception in this view is usually transient and self-
resolving; a dense cluster of them, or the same message repeating, is the
signal worth acting on - which the plain `last_exception` field alone can't
distinguish.

## Pattern: reconcile row counts against the source system

Verify a CDC/ingestion pipeline actually caught up by comparing a row count
at the source against the row count landed in ClickHouse for the same
logical object, rather than trusting consumer lag alone:

```sql
SELECT '$OBJECT_NAME' AS object,
       (SELECT count() FROM $SOURCE_DATABASE.$SOURCE_TABLE) AS source_count,
       (SELECT count() FROM $CH_DATABASE.$CH_VIEW) AS clickhouse_count;
```

Run this per object rather than reconciling a whole schema in one query - a
single mismatched table shouldn't get averaged out by dozens of matching
ones. Compare against a deduplicating view, not the raw landing table (see
the query-patterns reference), or ordinary merge lag will look like a
reconciliation failure.

A cheap freshness check that doesn't require a join to the source at all:

```sql
SELECT max(_inserted_timestamp) FROM $CH_DATABASE.$LANDING_TABLE;
```

How far behind "now" that value is says how fresh the pipeline is,
independent of whatever `system.kafka_consumers` reports about the consumer
itself - the two can disagree, and the landing table's own data is the
ground truth for what actually arrived.

## Rule: repoint the new writer before retiring the old one

When migrating which pipeline writes a table (moving from a legacy consumer
to a new one, or cutting over a target table), repoint the new
consumer/MV to the target table first, and retire the old one second. Verify
the key overlap between both branches before the switch, so a brief
double-write window gets absorbed by `ReplacingMergeTree` deduplication
instead of leaving the target table without an active writer during the
transition.
