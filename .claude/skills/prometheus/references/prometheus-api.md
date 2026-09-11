# Prometheus HTTP API reference

Generic reference for the Prometheus HTTP API. All examples use a placeholder host — substitute the real base URL supplied by the user, never hardcode one.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/query` | Instant query — value(s) at a single point in time (default: now) |
| `GET /api/v1/query_range` | Range query — value(s) over `start`..`end` at `step` intervals |
| `GET /api/v1/label/__name__/values` | List every metric name currently exposed |
| `GET /api/v1/label/<label>/values` | List every value seen for a given label (e.g. `job`, `pod`, `instance`) |
| `GET /api/v1/series` | List time series matching a set of label matchers, without values |

All are read-only GETs. Query parameters should be URL-encoded — use `curl -G --data-urlencode` rather than hand-encoding.

## Instant query

```bash
curl -sS -G "$PROMETHEUS_URL/api/v1/query" \
  --data-urlencode 'query=up{job="example-service"}' \
  --max-time 15 \
  | jq -r '.data.result[:20][] | [(.metric.instance // "unknown"), .value[1]] | @tsv'
```

Response shape:

```json
{"status":"success","data":{"resultType":"vector","result":[{"metric":{...},"value":[1690000000,"1"]}]}}
```

## Range query

Build `start`/`end` as Unix timestamps and pick a `step` that keeps the point count reasonable (a 24h range at `step=600` is 144 points).

```bash
START=$(date -u -v-24H +%s 2>/dev/null || date -u -d '24 hours ago' +%s)
END=$(date -u +%s)

curl -sS -G "$PROMETHEUS_URL/api/v1/query_range" \
  --data-urlencode 'query=rate(http_requests_total[5m])' \
  --data-urlencode "start=$START" \
  --data-urlencode "end=$END" \
  --data-urlencode 'step=600' \
  --max-time 20
```

`date -v` is macOS/BSD; `date -d` is GNU/Linux — try both so the same command works cross-platform.

## Discovering metric and label names

Don't guess a metric name — list what actually exists, then narrow with `grep`:

```bash
curl -sS "$PROMETHEUS_URL/api/v1/label/__name__/values" --max-time 15 \
  | jq -r '[.data[] | select(test("<keyword>"; "i"))][:50][]'
```

List values for a specific label (e.g. every `job` currently scraped):

```bash
curl -sS "$PROMETHEUS_URL/api/v1/label/job/values" --max-time 15 \
  | jq -r '.data[:50][]'
```

## PromQL basics

- Instant vector: `up` — current value of every series for that metric.
- Filter by label: `up{job="my-service"}`.
- Regex label match: `up{job=~"my-service.*"}`.
- Rate over a window (for counters): `rate(http_requests_total[5m])`.
- Aggregate across a label: `sum by (job) (rate(http_requests_total[5m]))`.
- Compare/threshold: `up == 0` — series currently down.

Counters (`_total` suffix) need `rate()` or `increase()` before they're meaningful; gauges can be read directly.

## Parsing responses

```bash
# single scalar value out of an instant query
curl -sS "$PROMETHEUS_URL/api/v1/query" \
  --data-urlencode 'query=up{job="example-service"}' --max-time 15 \
  | jq -r '.data.result[0].value[1]'

# metric + value pairs out of a vector result
curl -sS "$PROMETHEUS_URL/api/v1/query" \
  --data-urlencode 'query=up{job="example-service"}' --max-time 15 \
  | jq -r '.data.result[:20][] | "\(.metric.instance)=\(.value[1])"'

# byte value converted to GiB without changing units by hand
curl -sS "$PROMETHEUS_URL/api/v1/query" \
  --data-urlencode 'query=process_resident_memory_bytes{job="example-service"}' \
  --max-time 15 \
  | jq -r '.data.result[:20][] | [(.metric.instance // "unknown"), ((.value[1] | tonumber) / 1073741824)] | @tsv'
```

## Timeouts and cardinality

- Always set `--max-time` — an unbounded query against a wide range or high-cardinality label set can hang.
- Prefer aggregating (`sum`, `avg`) server-side over pulling every raw series and aggregating client-side.
- Project only needed labels and values with `jq`; never return complete metric
  label maps to the model.
- A display cap is a guard, not analysis. If results exceed it, narrow the label
  selector or aggregate in PromQL before drawing a conclusion.

## Grafana panel queries

When the user references a specific dashboard panel, extract and run its actual
query. A hand-written approximation can omit label filters, double-count
container and pod-level series, or use a different aggregation.

1. Extract the dashboard UID and panel ID from the URL. Fetch `GET
   $GRAFANA_URL/api/dashboards/uid/<uid>`; add authentication only if required.
2. Find the matching panel recursively in `dashboard.panels[]` and read its
   `targets[].expr`.
3. Substitute the current `var-*` URL parameter values for the dashboard
   variables in the expression.
4. Run that expression against `/api/v1/query`, then interpret its labels,
   aggregation, and units exactly as configured.
