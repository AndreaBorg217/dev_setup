---
name: prometheus
description: Use when querying Prometheus for metrics — instant/range queries, PromQL, or discovering metric/label names.
---

# Prometheus

Load this skill once before the first Prometheus query in a task. Keep its instructions active for the rest of that task.

## Establish the base URL

Prometheus's base URL is never hardcoded here. If it isn't already known from the current conversation or environment, ask the user for it before running any query. Do not guess a host from unrelated context.

## Use the reference

The workflow below is sufficient for ordinary instant queries. Read
[references/prometheus-api.md](references/prometheus-api.md) when the task needs
range queries, metric discovery, or Grafana panel extraction.

## Query workflow

1. Confirm the base URL.
2. If the exact metric or label name isn't known, discover it first via `/api/v1/label/__name__/values` or `/api/v1/label/<name>/values` rather than guessing.
3. Filter every metric to the named service, workload, namespace, pod, job, or instance. Never query a fleet-wide metric when the target is already known.
4. Pick instant query (`/api/v1/query`) for a single point in time, or range query (`/api/v1/query_range`) for a series over a window.
5. Aggregate in PromQL when the question asks for an aggregate. Otherwise project only the labels and values needed, and cap displayed series or samples at the source.
6. Set a request timeout on every call; Prometheus can be slow on wide time ranges or high-cardinality queries.
7. Parse the JSON response with a compact `jq` projection. Do not return the raw response or full metric label maps to the conversation.

For a bounded instant-vector result:

```bash
curl -sS -G "$PROMETHEUS_URL/api/v1/query" \
  --data-urlencode 'query=<metric>{<target-label>="<target>"}' \
  --max-time 15 \
  | jq -r '
      if .status != "success" then error(.error // "Prometheus query failed")
      else .data.result[:20][]
      | [(.metric.pod // .metric.instance // "unknown"), .value[1]]
      | @tsv
      end'
```

If more than 20 series are relevant, narrow or aggregate the PromQL rather than
silently relying on the display cap.

## Units and causal claims

- Convert byte metrics programmatically. Use `tonumber / 1073741824` for GiB or
  `tonumber / 1000000000` for GB, and label the result with the matching unit.
- Do not infer a native-memory owner from `RSS - used heap`. For JVM memory
  diagnosis, also inspect committed heap, non-heap, buffer pools, container
  working set/RSS, restarts, and any component-specific native metrics or
  configuration. Call an owner such as RocksDB probable until direct evidence
  identifies it.

## When the user references a Grafana panel

Read the Grafana-panel procedure in
[references/prometheus-api.md](references/prometheus-api.md). Extract and run
the panel's actual expression; do not approximate it with hand-written PromQL.

## Keep it generic

Do not write company names, internal hostnames, ticket keys, usernames, or internal topic/service names into this skill or its reference file. Use placeholder hosts (e.g. `$PROMETHEUS_URL`, `prometheus.example.com`) and generic metric names (e.g. `up`, `http_requests_total`) in any example added here.

## Scope

This skill covers read-only querying only. It does not cover Prometheus admin endpoints (snapshot, delete series, config reload) or Alertmanager.
