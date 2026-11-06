# Parts maintenance reference

A detached part is stored on disk but excluded from being queried by a
`SELECT`. `system.parts` and `system.detached_parts` expose the physical
reality behind a MergeTree table - what's merged, what's stuck, what's
detached, and why.

## Move a part between storage tiers

For MergeTree tables, move a part to a configured disk or volume:

```sql
ALTER TABLE $DATABASE.$TABLE MOVE PART '$PART_NAME' TO DISK '$DESTINATION_DISK';
ALTER TABLE $DATABASE.$TABLE MOVE PART '$PART_NAME' TO VOLUME '$DESTINATION_VOLUME';
```

Choose one command. For S3 to EBS, use the local disk or JBOD volume as the
destination; for EBS to S3, use the object-storage disk or volume. The command
is the same in either direction. The destination must be configured and
allowed by the table's storage policy; inspect `system.disks` and
`system.storage_policies` for the actual names.

The move applies only to the server receiving the command and is not
replicated. Inspect part names and locations on each replica separately.
Verify the result on that server:

```sql
SELECT name, disk_name
FROM system.parts
WHERE database = '$DATABASE' AND table = '$TABLE'
  AND name = '$PART_NAME' AND active;
```

## How parts get detached

- A failed `INSERT`, merge, or `ALTER`.
- Manual `ALTER TABLE ... DETACH PART` - be careful on a replicated table:
  this runs on all replicas, not just the one you ran it from.
- ClickHouse detaching parts itself to keep replicas consistent when they
  disagree.

## Reading the detach reason from the part's prefix

| Prefix | Meaning | What to do |
|---|---|---|
| `ignored_` | Inactive part superseded by a successful merge | Delete |
| `broken_`, `broken-on-start_`, `covered-by-broken_` | Corrupted on disk | Fetch a healthy copy from another replica |
| `attaching_`, `deleting_`, `tmp-fetch_` | Work already in progress (`ATTACH`, `DROP DETACHED PART`, replication) | Do not touch - monitor until the prefix resolves |
| `clone_` | ClickHouse detached it while repairing a replica | Delete once that replica has synced |
| `broken-from-backup_` | A `RESTORE` failed to restore this part | Check backup integrity before retrying |
| `unexpected` | A part ClickHouse doesn't expect to exist | Delete only if its data is covered by an active partition |
| `noquorum` | An `INSERT` ran locally but not enough replicas acknowledged | Check whether other replicas have the data (`system.parts` via `clusterAllReplicas`) before assuming it's lost |
| `merge-not-byte-identical`, `mutate-not-byte-identical` | This replica's merge/mutation checksum didn't match another replica's | Replication resolves this on its own |

## Detect, delete, and attach

```sql
-- what's detached, and why
SELECT name, reason, partition_id, min_block_number, max_block_number
FROM system.detached_parts
WHERE database = '$DATABASE' AND table = '$TABLE';

-- delete a specific detached part
ALTER TABLE $DATABASE.$TABLE DROP DETACHED PART '$PART_NAME';

-- reattach a specific detached part
ALTER TABLE $DATABASE.$TABLE ATTACH PART '$PART_NAME';
```

## Fetching a part from a healthy replica

```sql
-- 1. find the replication path
SELECT database, table, zookeeper_path, replica_name
FROM system.replicas
WHERE database = '$DATABASE' AND table = '$TABLE';

-- 2. fetch it from that path, then attach
ALTER TABLE $DATABASE.$TABLE FETCH PART '$PART_NAME' FROM '$ZOOKEEPER_PATH';
ALTER TABLE $DATABASE.$TABLE ATTACH PART '$PART_NAME';

-- if a replica is simply missing a part it should have
SYSTEM SYNC REPLICA $DATABASE.$TABLE;
```

## Is a replica actually caught up, or still syncing?

```sql
SELECT
    r.replica_name,
    multiIf(
        r.is_readonly OR r.is_session_expired, 'UNHEALTHY',
        r.log_pointer <= r.log_max_index OR coalesce(q.pending_part_sync_ops, 0) > 0, 'SYNCING',
        'SYNCED'
    ) AS status
FROM system.replicas AS r
LEFT JOIN (
    SELECT database, table, replica_name,
           countIf(type IN ('GET_PART', 'ATTACH_PART')) AS pending_part_sync_ops
    FROM system.replication_queue
    GROUP BY database, table, replica_name
) AS q USING (database, table, replica_name)
WHERE r.database = '$DATABASE' AND r.table = '$TABLE';
```

`SYNCING` means don't clean anything up yet. `SYNCED` means no outstanding
replication-log entries and no pending part fetch/attach. `UNHEALTHY` means
investigate the replica itself before touching its parts.

## Is a detached part already covered by an active part?

A part name encodes its partition, its block-number range, and its merge
level (e.g. `202609_100_120_3`). If a currently active part on the same
partition already spans the detached part's block range, the detached part
is redundant and safe to delete:

```sql
SELECT d.name AS detached_part, p.name AS covering_active_part,
       d.partition_id,
       d.min_block_number AS detached_min, d.max_block_number AS detached_max,
       p.min_block_number AS active_min, p.max_block_number AS active_max
FROM system.detached_parts AS d
INNER JOIN system.parts AS p
    ON p.database = d.database AND p.table = d.table
    AND p.partition_id = d.partition_id AND p.active = 1
    AND p.min_block_number <= d.min_block_number
    AND p.max_block_number >= d.max_block_number
WHERE d.database = '$DATABASE' AND d.table = '$TABLE' AND d.name = '$PART_NAME';
```

## Do other replicas already have the parts that cover this one?

Useful for the `noquorum` case above - confirm the data actually exists
somewhere in the cluster before treating a detached part as lost:

```sql
WITH detached AS (
    SELECT partition_id, min_block_number, max_block_number
    FROM system.detached_parts
    WHERE database = '$DATABASE' AND table = '$TABLE' AND name = '$PART_NAME'
    LIMIT 1
)
SELECT hostName() AS replica, p.name AS part
FROM clusterAllReplicas('$CLUSTER', system.parts) AS p
CROSS JOIN detached AS d
WHERE p.database = '$DATABASE' AND p.table = '$TABLE' AND p.active
  AND p.partition_id = d.partition_id
  AND p.min_block_number <= d.min_block_number
  AND p.max_block_number >= d.max_block_number;
```

## Frozen parts: don't forget they exist

`ALTER TABLE ... FREEZE` (often taken before a risky operation, as a manual
backup mechanism) leaves parts pinned on disk indefinitely until explicitly
unfrozen or cleaned up - they don't show up in ordinary size/row-count
queries against the table, only in `system.parts` directly:

```sql
SELECT name, database, table FROM system.parts WHERE is_frozen;
```

An empty result is the healthy state. A nonempty one is disk space held by a
freeze that may have been forgotten, not an error.

## Fragmented partitions: find OPTIMIZE candidates before running it blind

`OPTIMIZE TABLE ... FINAL` on every table on a schedule is expensive and
often unnecessary. Find which partitions actually have more than one active
part first, and target only those:

```sql
SELECT parts.partition_id, parts.database, parts.table, tables.engine,
       count() AS part_count
FROM system.parts AS parts
INNER JOIN system.tables AS tables
    ON tables.name = parts.table AND tables.database = parts.database
WHERE parts.active = 1
  AND tables.engine LIKE '%MergeTree%'
GROUP BY parts.partition_id, parts.database, parts.table, tables.engine
HAVING count() > 1
ORDER BY part_count DESC;
```

## Deciding whether a ReplacingMergeTree partition actually needs OPTIMIZE FINAL

A no-version `ReplacingMergeTree` only deduplicates on merge - and a merge
can happen across parts, but a *single freshly-inserted part* can itself
already contain duplicate keys if the same key was inserted more than once
in one batch. So "which partitions were touched recently" is not the same
question as "which partitions still have duplicates right now" - checking
only the first without the second either OPTIMIZEs partitions that don't
need it, or misses ones that do.

1. Find partitions touched since some cutover point using
   `system.parts.modification_time` rather than a business-time column on
   the data itself - any insert creates a part regardless of which business
   process wrote it or what time range its rows cover, so this catches
   writers whose business-time values fall outside the window you'd
   otherwise expect to check:

```sql
SELECT DISTINCT partition_id FROM system.parts
WHERE database = '$DATABASE' AND table = '$TABLE' AND active
  AND modification_time >= $CUTOVER;
```

2. Within just those partitions, check whether the table's actual
   deduplication key still has duplicate rows (`GROUP BY` the full key,
   `HAVING count() > 1`) - only those partitions need `OPTIMIZE ... FINAL`;
   a clean incremental write that inserted only new keys needs none.

3. If that `GROUP BY` scans a very large touched-partition set (e.g. because
   one writer does a full historical rescan and therefore "touches" every
   partition by this definition), bound the query's memory rather than
   letting it OOM: `SETTINGS max_bytes_before_external_group_by = $BYTES`
   forces the aggregation to spill to disk past that threshold instead of
   building an unbounded in-memory hash table. This changes nothing about
   the result - it only bounds peak memory - so it's safe to add whenever a
   full-key `GROUP BY` over a large touched set is a memory risk.
