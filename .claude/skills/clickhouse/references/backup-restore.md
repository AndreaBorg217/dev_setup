# Backup / restore reference

## Monitor an in-progress BACKUP or RESTORE from system.backups

`system.backups` is the native, always-available source of truth for any
`BACKUP`/`RESTORE` currently running or recently finished:

```sql
-- restores in progress, with the actual query text
SELECT sb.status, sb.start_time, sb.end_time,
       formatReadableTimeDelta(dateDiff('second', sb.start_time,
           if(toUnixTimestamp(sb.end_time) = 0, now(), sb.end_time))) AS duration,
       sq.query, sb.query_id
FROM system.backups AS sb
INNER JOIN system.query_log AS sq ON sq.query_id = sb.query_id
WHERE sb.status = 'RESTORING' AND sq.type = 'QueryStart'
ORDER BY sb.end_time DESC;

-- restore progress as a percentage
SELECT status,
       round(bytes_read / total_size * 100, 2) AS progress_pct,
       start_time,
       formatReadableTimeDelta(now() - start_time) AS duration,
       formatReadableSize(bytes_read) AS read_bytes,
       formatReadableSize(total_size) AS total_bytes
FROM system.backups
WHERE status = 'RESTORING'
ORDER BY start_time ASC;

-- backups in progress, same shape
SELECT sb.status, sq.query, sb.start_time, sb.end_time, sb.query_id,
       formatReadableSize(sb.total_size) AS total_size,
       formatReadableSize(sb.compressed_size) AS compressed_size
FROM system.backups AS sb
INNER JOIN system.query_log AS sq ON sq.query_id = sb.query_id
WHERE sb.status = 'CREATING_BACKUP' AND sq.type = 'QueryStart';
```

Joining to `system.query_log` on `query_id` recovers the actual `BACKUP`/
`RESTORE` statement that was run - useful when several operations are
in flight and `system.backups` alone doesn't say which table or destination
a given row belongs to.

## Sanity-check restore completeness by counting landed objects

Before trusting a restore is done, count what has actually landed rather
than only trusting the reported status - a restore that reports success but
landed fewer objects than expected is a real failure mode:

```sql
SELECT count() FROM system.tables WHERE database = '$RESTORE_TARGET_DATABASE';
```

Compare against the expected object count from the backup plan (or from
`system.backups.num_files`/the source environment's own table count) rather
than eyeballing whether the number "looks about right."

## Check where restored data is actually living

A restore/DR-verification database can end up with parts split across
storage tiers (local disk vs. object storage), which matters for both cost
and read latency. Check active parts per table, excluding the tiered/remote
disk, to see what's actually sitting on local storage:

```sql
SELECT table, disk_name, count() AS active_parts,
       formatReadableSize(sum(bytes_on_disk)) AS total_bytes
FROM system.parts
WHERE database = '$DATABASE' AND active = 1 AND disk_name != '$REMOTE_DISK_NAME'
GROUP BY table, disk_name
ORDER BY table, disk_name;
```

## Keep your own backup run history, and query it directly

If backup/restore operations are logged to a table of your own (recording
`backup_id`, `source_table`, `action`, `status`, `started_at`, `finished_at`,
destination, size), query it directly for history rather than re-deriving
the same facts from `system.backups` each time (which only covers currently
tracked operations, not full historical audit):

```sql
SELECT backup_id, kind, dest_url, started_at, finished_at
FROM $RUN_LOG_TABLE
WHERE env = '$ENV' AND action = 'backup' AND status = 'success'
  AND source_table = '$SOURCE_TABLE'
ORDER BY finished_at DESC
LIMIT 5;
```

`SHOW CREATE $RUN_LOG_TABLE` first if the exact column set isn't already
known - a hand-maintained log table's schema isn't guaranteed to match any
convention.

## Measure before tuning concurrency

Correlate `system.metric_log` with what a slow backup/restore job is
actually bottlenecked on before changing any concurrency setting:

```sql
SELECT toStartOfHour(event_time) AS h,
       round(avg(CurrentMetric_$THREAD_POOL_METRIC), 1) AS threads_active,
       round(avg(ProfileEvent_$IO_METRIC), 1)           AS io_ops_per_s,
       round(avg(ProfileEvent_OSCPUVirtualTimeMicroseconds)/1e6, 2) AS cpu_cores
FROM clusterAllReplicas('$CLUSTER', system.metric_log)
WHERE event_time >= $START AND event_time < $END AND hostName() = '$HOST'
GROUP BY h HAVING threads_active > 0 ORDER BY h
```

Low CPU with a saturated thread pool and high I/O activity means the
bottleneck is I/O latency (object storage, network), not compute - raising
concurrency without raising the thread pool just starves the existing
threads further. Cross-check against infrastructure metrics (container CPU
vs requested CPU) before concluding the database itself is undersized.

Concurrent native operations can also contend for one shared connection or
thread pool and end up slower in aggregate than running them serially - more
parallelism doesn't always help once a shared resource is the actual
bottleneck. Prove concurrency is helping with a real before/after comparison
of wall time (via `system.backups`/your run log, above), not by assumption -
and when comparing two configurations, change one variable at a time.
