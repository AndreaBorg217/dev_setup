# Query patterns reference

## Check pruning before assuming a query is slow

A query that filters only on a column outside the table's `ORDER BY` key and
`PARTITION BY` key forces a full scan - ClickHouse can't skip parts or
granules on it. Before optimizing anything else, confirm what's actually
happening:

```sql
EXPLAIN indexes = 1
SELECT ...
FROM $TABLE
WHERE $FILTER_COLUMN = $VALUE
```

Check the table's actual sort and partition keys without a full
`SHOW CREATE TABLE`:

```sql
SELECT sorting_key, partition_key FROM system.tables
WHERE database = '$DATABASE' AND name = '$TABLE'
```

If the filtered column isn't in `sorting_key` or `partition_key`, add a bound
on a column that is (even a wide one) before filtering on the column that
isn't - partition pruning and the min-max skip index only help columns
correlated with the key you actually bounded. A predicate reliably prunes
only when it constrains a left-anchored prefix of the sort key; a filter on
a later key column alone can still prune opportunistically depending on data
layout, but `EXPLAIN` is the only way to know either way - don't guess from
the query shape.

Two tables that look similar can have very different partition keys - always
read `partition_key` for the specific table rather than assuming it matches
a sibling table, and filter the column the partition expression actually
names (a table with both a `date` and a `time` column holding the same
instant can have a partition key derived only from `time`, in which case
filtering on `date` prunes nothing).

## Never read a ReplacingMergeTree table without deduplicating - FINAL or argMax, depending on performance

`ReplacingMergeTree` (and `ReplicatedReplacingMergeTree`) only deduplicates
rows when parts get merged - a raw `count()`, `sum()`, or `max()` against the
table can double-count rows that haven't merged yet, silently and without
error. There are two correct ways to read it, and which one to reach for
depends on cost, not on which is "more correct" - both are correct:

**`FINAL`** - simplest, and correct by construction:

```sql
SELECT * FROM $TABLE FINAL WHERE $FILTER = $VALUE;
```

It merges on the fly at query time, which makes it the expensive option on a
wide or large table. Filtering on the table's key columns in the same query
keeps the cost down, since `FINAL` then only has to merge the parts that
predicate actually touches.

**Manual `argMax` dedup** - faster than `FINAL` on wide/large tables, but
only usable when the table declares a version column (check `engine_full` -
`ReplacingMergeTree(ver[, is_deleted])`; a bare `ReplacingMergeTree()` has no
version column to rank by, and `FINAL` is the only option then):

```sql
SELECT $KEY_COLUMNS,
       argMax($VALUE_COLUMN, $VER_COLUMN) AS $VALUE_COLUMN,
       max($VER_COLUMN) AS version
FROM $TABLE
WHERE $FILTER = $VALUE
GROUP BY $KEY_COLUMNS;
```

Two rules that are easy to get wrong when hand-rolling this: `GROUP BY` must
cover the table's *entire* sorting key, not just an id column (grouping on a
prefix silently merges rows that are genuinely distinct); and if the table
also declares `is_deleted`, soft-deleted rows are not filtered
automatically the way `FINAL` filters them - add
`HAVING argMax(is_deleted, $VER_COLUMN) = 0` explicitly, and never substitute
a plain `WHERE is_deleted = 0` for it (a plain filter can resurrect an older
non-deleted version of a row that was in fact later deleted).

If a schema already exposes a pre-built view that applies one of these two
patterns for you, prefer that view over reimplementing either pattern by
hand - check what the view's definition actually does rather than trusting
its name; a naming convention is not a guarantee.

Check how stale a non-deduplicated read would be right now by counting
unmerged (`level = 0`) parts:

```sql
SELECT partition, count() AS unmerged_parts, sum(rows) AS rows
FROM system.parts
WHERE database = '$DATABASE' AND table = '$TABLE' AND active AND level = 0
GROUP BY partition ORDER BY unmerged_parts DESC
```

Many `level = 0` parts means recent inserts haven't merged yet, so a raw
read is returning duplicates right now, not hypothetically.

## Access control introspection

Check what's actually granted before assuming a permission problem is code,
not access:

```sql
SHOW GRANTS FOR '$ROLE_OR_USER';
SHOW CREATE USER '$USER';
```

Find which quota governs a user - by explicit membership or by a catch-all
default, which is easy to miss if only `apply_to_list` is checked:

```sql
SELECT name, apply_to_list, apply_to_all
FROM system.quotas
WHERE apply_to_all OR has(apply_to_list, '$USER');
```

Change a quota or settings-profile assignment cluster-wide rather than only
on the node currently connected to:

```sql
ALTER QUOTA '$QUOTA_NAME' ON CLUSTER '$CLUSTER' TO '$USER';
ALTER USER '$USER' ON CLUSTER '$CLUSTER' SETTINGS PROFILE '$PROFILE_NAME';
```

Check which row-level policies apply to a table before assuming a query's
missing rows are a bug:

```sql
SELECT name, database, table, select_filter, apply_to_all, apply_to_list
FROM system.row_policies
WHERE table = '$TABLE';
```

A `select_filter` here silently narrows every `SELECT` against the table for
whichever role/user it applies to - a query that looks wrong may be
correctly filtered, not broken.

## Diagnosing a query that's already slow

1. Run `EXPLAIN indexes = 1` on it first - a high granule/part ratio at any
   index stage is a pruning failure, and the fix is a predicate change, not a
   settings change.
2. Re-read `sorting_key`/`partition_key` for the actual table - a slow query
   is often written against a schema that changed since it was last correct.
3. Compare rows read to rows returned (`system.query_log` on a replicated
   cluster needs `clusterAllReplicas(...)`, since a node-local read only sees
   a fraction of traffic and double-counts distributed child queries if you
   don't filter to `is_initial_query = 1`). A large `read_rows` against a
   tiny `result_rows` is the pruning-failure signature; high `memory_usage`
   with modest `read_rows` points at a `GROUP BY`/`JOIN` blowing up instead.
4. Check whether deduplication (`FINAL` or `argMax`) is the cost - time the
   query with and without it.
5. Change one variable at a time when comparing two versions of a query -
   filesystem cache means a second run is always warmer than the first, so
   compare `read_rows` from `system.query_log` rather than wall-clock time.

## Reading a query plan

Run the `EXPLAIN` variants in this order; each answers a different question.

```sql
EXPLAIN PLAN actions = 1, indexes = 1 SELECT ...;
EXPLAIN PIPELINE SELECT ...;
EXPLAIN ESTIMATE SELECT ...;
```

- **`EXPLAIN PLAN actions = 1, indexes = 1`** - read the `ReadFromMergeTree`
  node: per index (`Partition`, `PrimaryKey`, each `Skip`) the `Parts` and
  `Granules` are `after/before`. A ratio near 1/1 means that stage pruned
  nothing. Then look at the step order: a `Filter` above the read rather than
  `Prewhere info`, an `Aggregating`/`Sorting` over far more rows than needed,
  or `FINAL`/`Join` steps sitting on the full table. Set `actions = 1`
  explicitly: the default differs by version, and `json = 1` does not enable
  it. From v25.9, `indexes = 1` is only reliable with
  `SETTINGS use_query_condition_cache = 0, use_skip_indexes_on_data_read = 0`.
  Add `projections = 1` to see whether a projection was analysed.
- **`EXPLAIN PIPELINE`** - shows the parallelism, not the logic. Look for a
  `Resize N -> 1` followed by a long single-threaded chain (a serialisation
  point), and for `Join`/`Sorting` processors that run on one stream.
  `graph = 1` prints DOT for large pipelines.
- **`EXPLAIN ESTIMATE`** - estimated `parts`, `rows` and `marks` per table
  (MergeTree family only). Run it before and after a predicate or key change
  to compare the work without executing the query.

## Profiling from `system.query_log`

`read_rows`, `read_bytes`, `memory_usage` and `query_duration_ms` are columns.
`ProfileEvents` is a map, so pull named counters directly. Use the same
initial-query and `clusterAllReplicas` rules as the diagnosing section above.

```sql
SELECT
    query_duration_ms, read_rows, result_rows,
    formatReadableSize(memory_usage) AS peak_memory,
    ProfileEvents['SelectedParts']  AS parts,
    ProfileEvents['SelectedMarks']  AS marks,
    ProfileEvents['SelectedMarksTotal'] AS marks_total
FROM system.query_log
WHERE type = 'QueryFinish' AND is_initial_query = 1
  AND normalized_query_hash = $HASH
ORDER BY event_time DESC
LIMIT 10
```

`SelectedMarks` against `SelectedMarksTotal` is the pruning ratio in one
line. `normalized_query_hash` groups runs of the same query shape across
different literals.

## Optimisation catalogue

Work from the plan, not from this list: pick an item only when the plan shows
the problem it fixes.

- **`PREWHERE`** - ClickHouse moves eligible `WHERE` conditions automatically
  (`optimize_move_to_prewhere`). Write it explicitly only when a condition on
  few columns removes most rows and the automatic choice did not pick it
  (check `Prewhere info` in the plan). With `FINAL`, `PREWHERE` runs before
  deduplication, so it is only safe on `ORDER BY` key columns.
- **Skip indexes** (`minmax`, `set(N)`, `bloom_filter`) - only help when the
  filtered column's values are clustered per granule, i.e. correlated with the
  sort key. `minmax` suits ranges on loosely ordered numbers/times, `set` low
  cardinality equality/`IN`, `bloom_filter` many discrete values (also arrays
  and maps). Confirm the `Skip` row in `EXPLAIN indexes = 1` drops granules;
  an index that prunes nothing only costs insert and merge time. Existing
  parts need `ALTER TABLE ... MATERIALIZE INDEX`.
- **Projections** - an alternative sort order or pre-aggregate stored inside
  the table. Use when one table must serve a second filter pattern or a
  repeated aggregate. The query must reference the projection's stored
  columns directly (`optimize_use_projections` is on by default); old parts
  need materialising.
- **`ORDER BY` key fit** - put columns used in equality filters first, and
  low-cardinality before high. A key that does not match the dominant filter is
  the usual root cause of a full scan; changing it means a new table.
- **Joins** - the right table is the one held in memory (the `hash` build
  side), so put the smaller table on the right. Move a large-vs-large join to
  `grace_hash` or `full_sorting_merge` through `join_algorithm` only when
  `memory_usage` is the problem. Filter both sides before the join, and prefer
  `dictGet` for small dimension lookups.
- **Pre-aggregation with a materialized view** - when the same large
  `GROUP BY` runs repeatedly, aggregate on insert into a `SummingMergeTree` /
  `AggregatingMergeTree` target and query that. Costs extra write work and
  only covers data inserted after the view exists.
- **`LowCardinality` and codecs** - `LowCardinality(String)` helps columns
  with few distinct values (less storage, faster filter and `GROUP BY`);
  it is counter-productive on high-cardinality columns. Per-column `CODEC`
  (for example `Delta, ZSTD` on monotonic values) cuts bytes read at some CPU
  cost. Both are schema changes.

## Proposal format

State every suggestion as four lines so it can be accepted or rejected on
evidence:

1. **Change** - the exact predicate, DDL or setting.
2. **Expected effect** - which metric moves and why, tied to a plan line
   (for example "`PrimaryKey` granules 9800/9800 should fall below 100").
3. **Risk and cost** - insert/merge overhead, storage, a table rebuild, or
   results that may change (`FINAL` with `PREWHERE`).
4. **Verification** - run before and after, then compare `read_rows`,
   `read_bytes` and `memory_usage` (and `SelectedMarks`) from
   `system.query_log` for the two runs. Do not compare wall-clock time.
