# Example panels

Generic snippets to adapt. `my_app_*` is a placeholder metric prefix, `job="my-app"` is the static scope. Replace both from the metric inventory. Each snippet shows only the fields that carry the house style. Add `id`, `gridPos` and the defaults Grafana expects when assembling the file.

Datasource object used everywhere:

```json
{ "type": "prometheus", "uid": "${datasource}" }
```

## Dashboard skeleton

```json
{
  "uid": "my_tech_overview",
  "title": "My Tech Overview",
  "description": "Fleet-level health, throughput and latency for My Tech.",
  "tags": ["my-tech", "my-subtech", "my-team"],
  "editable": true,
  "graphTooltip": 0,
  "refresh": "1m",
  "schemaVersion": 41,
  "fiscalYearStartMonth": 0,
  "links": [],
  "annotations": { "list": [{ "builtIn": 1, "datasource": { "type": "grafana", "uid": "-- Grafana --" }, "enable": true, "hide": true, "iconColor": "rgba(0, 211, 255, 1)", "name": "Annotations & Alerts", "type": "dashboard" }] },
  "time": { "from": "now-1h", "to": "now" },
  "timepicker": { "refresh_intervals": ["5s", "15s", "1m", "5m"] },
  "templating": { "list": [] },
  "panels": []
}
```

## Variables

Datasource, then a visible chain parent, a hidden plumbing child, and a natural-sorted leaf (`sort: 3`).

```json
[
  {
    "name": "datasource", "type": "datasource", "query": "prometheus",
    "label": "Datasource", "current": {}, "hide": 0
  },
  {
    "name": "app", "label": "Application", "type": "query",
    "datasource": { "type": "prometheus", "uid": "${datasource}" },
    "query": { "query": "label_values(my_app_state{job=\"my-app\"}, app)", "refId": "app" },
    "includeAll": true, "allValue": ".*", "multi": false,
    "refresh": 1, "sort": 0, "hide": 0
  },
  {
    "name": "instance", "type": "query",
    "datasource": { "type": "prometheus", "uid": "${datasource}" },
    "query": { "query": "label_values(my_app_state{job=\"my-app\", app=~\"$app\"}, instance)", "refId": "instance" },
    "includeAll": true, "allValue": ".*", "multi": true,
    "refresh": 1, "sort": 1, "hide": 2
  },
  {
    "name": "task", "label": "Task", "type": "query",
    "datasource": { "type": "prometheus", "uid": "${datasource}" },
    "query": { "query": "label_values(my_app_task_state{job=\"my-app\", app=~\"$app\"}, task)", "refId": "task" },
    "includeAll": true, "allValue": ".*", "multi": false,
    "refresh": 1, "sort": 3, "hide": 0
  }
]
```

## KPI stat: enum state with mappings

```json
{
  "type": "stat",
  "title": "State",
  "description": "Current lifecycle state of the selected application. Anything other than RUNNING for more than a few minutes needs investigation.",
  "datasource": { "type": "prometheus", "uid": "${datasource}" },
  "targets": [{
    "datasource": { "type": "prometheus", "uid": "${datasource}" },
    "editorMode": "code", "format": "time_series", "instant": true,
    "expr": "max(my_app_state{job=\"my-app\", app=~\"$app\"})",
    "legendFormat": "__auto", "refId": "A"
  }],
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "color": { "mode": "thresholds" },
      "thresholds": { "mode": "absolute", "steps": [{ "color": "green", "value": null }] },
      "mappings": [{ "type": "value", "options": {
        "0": { "text": "STARTING", "color": "orange" },
        "1": { "text": "RUNNING", "color": "green" },
        "2": { "text": "ERROR", "color": "red" }
      } }]
    },
    "overrides": []
  },
  "options": {
    "reduceOptions": { "calcs": ["lastNotNull"], "fields": "", "values": false },
    "colorMode": "background", "graphMode": "none", "textMode": "auto",
    "justifyMode": "center", "orientation": "auto"
  }
}
```

## KPI stat: rate with sparkline

```json
{
  "type": "stat",
  "title": "Records Processed",
  "description": "Records processed per second across the selected applications. A drop to zero while input is flowing means processing has stalled.",
  "targets": [{
    "editorMode": "code", "format": "time_series", "instant": false,
    "expr": "sum(rate(my_app_records_processed_total{job=\"my-app\", app=~\"$app\"}[5m]))",
    "legendFormat": "__auto", "refId": "A"
  }],
  "fieldConfig": { "defaults": { "unit": "ops", "min": 0, "color": { "mode": "thresholds" },
    "thresholds": { "mode": "absolute", "steps": [{ "color": "green", "value": null }] } }, "overrides": [] },
  "options": {
    "reduceOptions": { "calcs": ["lastNotNull"], "fields": "", "values": false },
    "colorMode": "value", "graphMode": "area", "textMode": "auto"
  }
}
```

## KPI stat: ratio with health thresholds

Reference `streams_summary_v2` #52. Red below 0.5, yellow to 1, green at 1 or above.

```json
{
  "type": "stat",
  "title": "Process / Input Ratio",
  "description": "Records processed per second divided by records consumed per second. Below 1.0 means the application is falling behind its input.",
  "targets": [{
    "editorMode": "code", "format": "time_series", "instant": true,
    "expr": "sum(my_app_process_rate{job=\"my-app\", app=~\"$app\"}) / (sum(rate(my_app_records_consumed_total{job=\"my-app\", app=~\"$app\"}[5m])) > 0)",
    "legendFormat": "__auto", "refId": "A"
  }],
  "fieldConfig": { "defaults": { "unit": "short", "decimals": 2, "color": { "mode": "thresholds" },
    "thresholds": { "mode": "absolute", "steps": [
      { "color": "red", "value": null }, { "color": "yellow", "value": 0.5 }, { "color": "green", "value": 1 }] } }, "overrides": [] },
  "options": {
    "reduceOptions": { "calcs": ["lastNotNull"], "fields": "", "values": false },
    "colorMode": "background", "graphMode": "none", "textMode": "auto"
  }
}
```

## KPI stat: breakdown of a whole

Reference `streams_thread_v2` #3, paired with the stacked share timeseries #2 (`stacking.mode=normal`, right table legend with `mean` and `lastNotNull`, description "should sum to about 1.0"). One instant target per part, legend per part. Only two of the parts are shown here.

```json
{
  "type": "stat",
  "title": "Current Time Split",
  "description": "Share of thread time spent in each phase right now. The shares should sum to about 1.0, a large poll share means the thread is waiting for input.",
  "targets": [
    { "editorMode": "code", "format": "time_series", "instant": true, "refId": "A", "legendFormat": "poll",
      "expr": "avg(my_app_poll_ratio{job=\"my-app\", app=~\"$app\"} <= +Inf)" },
    { "editorMode": "code", "format": "time_series", "instant": true, "refId": "B", "legendFormat": "process",
      "expr": "avg(my_app_process_ratio{job=\"my-app\", app=~\"$app\"} <= +Inf)" }
  ],
  "fieldConfig": { "defaults": { "unit": "percentunit", "min": 0, "color": { "mode": "thresholds" },
    "thresholds": { "mode": "absolute", "steps": [{ "color": "green", "value": null }] } }, "overrides": [] },
  "options": {
    "reduceOptions": { "calcs": ["lastNotNull"], "fields": "", "values": false },
    "colorMode": "background", "graphMode": "none", "textMode": "value_and_name", "orientation": "horizontal"
  }
}
```

## KPI stat: min and max range for skew

Reference `streams_task_v2` #16, paired with the trend timeseries #20 (right table legend, `mean`, `max`, `lastNotNull`). Same shape as the breakdown stat with two targets and `unit=ms`.

```json
{
  "targets": [
    { "editorMode": "code", "format": "time_series", "instant": true, "refId": "A", "legendFormat": "Min",
      "expr": "min by (app, subtopology) (my_app_e2e_latency_avg{job=\"my-app\", app=~\"$app\"} >= 0)" },
    { "editorMode": "code", "format": "time_series", "instant": true, "refId": "B", "legendFormat": "Max",
      "expr": "max by (app, subtopology) (my_app_e2e_latency_avg{job=\"my-app\", app=~\"$app\"} >= 0)" }
  ],
  "options": { "colorMode": "value", "graphMode": "none", "textMode": "value_and_name", "orientation": "horizontal" }
}
```

## KPI stat: error count with a meaningful threshold

```json
{
  "type": "stat",
  "title": "Errors",
  "description": "Errors recorded in the selected time range. Any non-zero value is worth checking, the dead-letter and application logs show the cause.",
  "targets": [{
    "editorMode": "code", "format": "time_series", "instant": true,
    "expr": "sum(increase(my_app_errors_total{job=\"my-app\", app=~\"$app\"}[$__range]))",
    "legendFormat": "__auto", "refId": "A"
  }],
  "fieldConfig": { "defaults": { "unit": "short", "min": 0, "noValue": "No errors recorded", "color": { "mode": "thresholds" },
    "thresholds": { "mode": "absolute", "steps": [
      { "color": "green", "value": null }, { "color": "red", "value": 1 }] } }, "overrides": [] },
  "options": {
    "reduceOptions": { "calcs": ["lastNotNull"], "fields": "", "values": false },
    "colorMode": "value", "graphMode": "none", "textMode": "auto"
  }
}
```

## Timeseries: rate by dimension, right-hand table legend

```json
{
  "type": "timeseries",
  "title": "Throughput by Topic",
  "description": "Records consumed per second for each topic in the selection. Use it to spot an uneven or stalled input.",
  "targets": [{
    "editorMode": "code", "format": "time_series",
    "expr": "sum by (topic) (rate(my_app_records_consumed_total{job=\"my-app\", app=~\"$app\"}[5m]))",
    "legendFormat": "{{topic}}", "refId": "A"
  }],
  "fieldConfig": {
    "defaults": {
      "unit": "ops", "min": 0,
      "color": { "mode": "palette-classic" },
      "custom": {
        "drawStyle": "line", "lineWidth": 1, "fillOpacity": 10, "gradientMode": "none",
        "showPoints": "never", "lineInterpolation": "smooth",
        "stacking": { "mode": "none", "group": "A" }, "spanNulls": false,
        "axisPlacement": "auto", "scaleDistribution": { "type": "linear" }
      }
    },
    "overrides": []
  },
  "options": {
    "legend": { "displayMode": "table", "placement": "right", "showLegend": true,
      "calcs": ["mean", "max", "lastNotNull"] },
    "tooltip": { "mode": "multi", "sort": "desc" }
  }
}
```

## Timeseries: average and maximum pair

```json
{
  "type": "timeseries",
  "title": "Process Latency",
  "description": "Average and maximum time to process one record. A growing maximum with a flat average points to a few slow records, both rising points to overload.",
  "targets": [
    { "editorMode": "code", "format": "time_series", "legendFormat": "Avg", "refId": "A",
      "expr": "avg(my_app_process_latency_avg{job=\"my-app\", app=~\"$app\"} >= 0)" },
    { "editorMode": "code", "format": "time_series", "legendFormat": "Max", "refId": "B",
      "expr": "max(my_app_process_latency_max{job=\"my-app\", app=~\"$app\"} >= 0)" }
  ],
  "fieldConfig": { "defaults": { "unit": "ms", "min": 0, "color": { "mode": "palette-classic" },
    "custom": { "drawStyle": "line", "lineWidth": 1, "fillOpacity": 10, "showPoints": "never",
      "stacking": { "mode": "none", "group": "A" }, "spanNulls": false } }, "overrides": [] },
  "options": {
    "legend": { "displayMode": "table", "placement": "right", "showLegend": true,
      "calcs": ["mean", "max", "lastNotNull"] },
    "tooltip": { "mode": "multi", "sort": "desc" }
  }
}
```

## Timeseries: usage against a limit

Dashed, lighter limit line through an override.

```json
{
  "fieldConfig": {
    "defaults": { "unit": "bytes", "min": 0, "color": { "mode": "palette-classic" } },
    "overrides": [{
      "matcher": { "id": "byRegexp", "options": ".*(limit|capacity|request).*" },
      "properties": [
        { "id": "custom.lineStyle", "value": { "fill": "dash", "dash": [10, 10] } },
        { "id": "custom.fillOpacity", "value": 0 }
      ]
    }]
  }
}
```

Targets: `legendFormat` of `{{pod}} usage` and `{{pod}} limit`.

## Timeseries: utilisation ratio

```json
{
  "fieldConfig": {
    "defaults": {
      "unit": "percentunit", "min": 0, "max": 1,
      "color": { "mode": "palette-classic" },
      "custom": { "thresholdsStyle": { "mode": "line+area" } },
      "thresholds": { "mode": "absolute", "steps": [
        { "color": "green", "value": null }, { "color": "orange", "value": 0.8 }, { "color": "red", "value": 0.95 }] }
    },
    "overrides": []
  }
}
```

## Timeseries: optional counter with zero fallback

```json
{
  "type": "timeseries",
  "title": "Dead-Letter Writes",
  "description": "Records written to the dead-letter topic per second. The counter only exists after the first failure, so a flat zero means nothing has been dead-lettered.",
  "targets": [{
    "editorMode": "code", "format": "time_series", "refId": "A",
    "expr": "sum(rate(my_app_dlq_records_total{job=\"my-app\", app=~\"$app\"}[5m])) or vector(0)",
    "legendFormat": "dead-letter"
  }],
  "fieldConfig": { "defaults": { "unit": "ops", "min": 0, "color": { "mode": "palette-classic" } }, "overrides": [] }
}
```

Other empty-data forms:

- Named zero series when nothing happened: `<expr> or label_replace(0 * absent(<expr>), "pod", "none", "", "")`.
- Ratio gauge that can be NaN in empty windows: `avg(avg_over_time(<ratio>[5m]) <= +Inf)`.

## Bargauge: ranked current values

```json
{
  "type": "bargauge",
  "title": "Busiest Topics",
  "description": "Current consumption rate per topic, highest first.",
  "targets": [{
    "editorMode": "code", "format": "time_series", "instant": true,
    "expr": "sort_desc(sum by (topic) (rate(my_app_records_consumed_total{job=\"my-app\", app=~\"$app\"}[5m])))",
    "legendFormat": "{{topic}}", "refId": "A"
  }],
  "fieldConfig": { "defaults": { "unit": "ops", "min": 0, "color": { "mode": "palette-classic" },
    "noValue": "No data (requires DEBUG metrics)" }, "overrides": [] },
  "transformations": [
    { "id": "sortBy", "options": { "fields": {}, "sort": [{ "field": "Value", "desc": true }] } }
  ],
  "options": {
    "orientation": "horizontal", "displayMode": "basic", "valueMode": "color",
    "showUnfilled": true, "minVizHeight": 16, "namePlacement": "auto",
    "reduceOptions": { "calcs": ["lastNotNull"], "fields": "", "values": false },
    "legend": { "displayMode": "list", "placement": "bottom", "showLegend": false }
  }
}
```

## Barchart: ranked comparison by entity

Reference `streams_topic_v2` #18. `w=24`, `h=12`. The instant query is wrapped in `sort_desc`, then `seriesToRows` and `sortBy` desc put the bars in order.

```json
{
  "type": "barchart",
  "title": "Consumed Load by Topic and Task",
  "description": "Records consumed per second for each topic and task, highest first. A few tall bars mean the load is uneven.",
  "targets": [{
    "editorMode": "code", "format": "time_series", "instant": true,
    "expr": "sort_desc(sum by (topic, task) (rate(my_app_records_consumed_total{job=\"my-app\", app=~\"$app\"}[5m])))",
    "legendFormat": "{{topic}} | {{task}}", "refId": "A"
  }],
  "transformations": [
    { "id": "seriesToRows", "options": {} },
    { "id": "sortBy", "options": { "fields": {}, "sort": [{ "field": "Value", "desc": true }] } }
  ],
  "fieldConfig": { "defaults": { "unit": "ops", "min": 0, "color": { "mode": "palette-classic" } }, "overrides": [] },
  "options": {
    "orientation": "vertical", "fillOpacity": 80,
    "legend": { "showLegend": false },
    "tooltip": { "mode": "single", "sort": "none" }
  }
}
```

## Table: inventory with renamed columns

```json
{
  "type": "table",
  "title": "Instances",
  "description": "One row per running instance with its uptime and current lag.",
  "targets": [
    { "editorMode": "code", "format": "table", "instant": true, "refId": "A",
      "expr": "min by (instance) (time() - process_start_time_seconds{job=\"my-app\"})" },
    { "editorMode": "code", "format": "table", "instant": true, "refId": "B",
      "expr": "sum by (instance) (my_app_consumer_lag{job=\"my-app\"})" }
  ],
  "transformations": [
    { "id": "merge", "options": {} },
    { "id": "organize", "options": {
      "excludeByName": { "Time": true },
      "renameByName": { "instance": "Instance", "Value #A": "Uptime", "Value #B": "Lag (records)" } } }
  ],
  "fieldConfig": { "defaults": {}, "overrides": [
    { "matcher": { "id": "byName", "options": "Uptime" }, "properties": [{ "id": "unit", "value": "s" }] }
  ] },
  "options": { "showHeader": true, "cellHeight": "sm",
    "sortBy": [{ "displayName": "Lag (records)", "desc": true }] }
}
```

## Event counts: period KPI and outcome pair

KPI stat over the selected range:

```json
{
  "type": "stat",
  "title": "Rebalances",
  "description": "Rebalances, successful and failed, in the selected time range. Frequent rebalances mean instances are restarting or losing their group membership.",
  "targets": [{
    "editorMode": "code", "format": "time_series", "instant": true,
    "expr": "sum(increase(my_app_rebalance_total{job=\"my-app\", app=~\"$app\"}[$__range])) + sum(increase(my_app_failed_rebalance_total{job=\"my-app\", app=~\"$app\"}[$__range]))",
    "legendFormat": "__auto", "refId": "A"
  }],
  "fieldConfig": { "defaults": { "unit": "short", "min": 0, "color": { "mode": "thresholds" },
    "thresholds": { "mode": "absolute", "steps": [{ "color": "green", "value": null }] } }, "overrides": [] },
  "options": {
    "reduceOptions": { "calcs": ["lastNotNull"], "fields": "", "values": false },
    "colorMode": "value", "graphMode": "none", "textMode": "auto"
  }
}
```

Bar timeseries with one target per outcome. The window is stated in the legend, the legend shows the sum, and idle series are hidden from the tooltip. Set `stacking.mode` to `normal` when the total matters more than comparing outcomes:

```json
{
  "type": "timeseries",
  "title": "Rebalances by Outcome",
  "description": "Successful and failed rebalances per application in 5 minute buckets. Failed rebalances point to unstable group membership.",
  "targets": [
    { "editorMode": "code", "format": "time_series", "refId": "A",
      "expr": "sum by (app) (increase(my_app_rebalance_total{job=\"my-app\", app=~\"$app\"}[5m]))",
      "legendFormat": "{{app}} | successful / 5m" },
    { "editorMode": "code", "format": "time_series", "refId": "B",
      "expr": "sum by (app) (increase(my_app_failed_rebalance_total{job=\"my-app\", app=~\"$app\"}[5m]))",
      "legendFormat": "{{app}} | failed / 5m" }
  ],
  "fieldConfig": { "defaults": { "unit": "short", "min": 0, "color": { "mode": "palette-classic" },
    "custom": { "drawStyle": "bars", "fillOpacity": 80, "lineWidth": 1, "showPoints": "never",
      "stacking": { "mode": "none", "group": "A" } } }, "overrides": [] },
  "options": {
    "legend": { "displayMode": "table", "placement": "right", "showLegend": true, "calcs": ["sum"] },
    "tooltip": { "mode": "multi", "sort": "desc", "hideZeros": true }
  }
}
```

## Table: usage against requests

Four instant targets merged on pod. Every operand is joined to the selected app. `C` and `D` repeat the `A` and `B` expressions divided by the request sum, written here as `<A expr>` and `<B expr>`.

```json
{
  "type": "table",
  "title": "Pod Resource Usage",
  "description": "CPU and memory per pod, and each as a share of the pod's requests. Cells turn yellow at 70% and red at 100%, which marks pods that are under-provisioned. Pods far below 70% are candidates for lower requests.",
  "targets": [
    { "refId": "A", "editorMode": "code", "format": "table", "instant": true,
      "expr": "sum by (pod) (rate(container_cpu_usage_seconds_total{container!=\"\",container!=\"POD\"}[5m]) * on(namespace,pod) group_left() kube_pod_labels{label_app=~\"$app\"})" },
    { "refId": "B", "editorMode": "code", "format": "table", "instant": true,
      "expr": "sum by (pod) (container_memory_working_set_bytes{container!=\"\",container!=\"POD\"} * on(namespace,pod) group_left() kube_pod_labels{label_app=~\"$app\"})" },
    { "refId": "C", "editorMode": "code", "format": "table", "instant": true,
      "expr": "<A expr> / sum by (pod) (kube_pod_container_resource_requests{resource=\"cpu\"} * on(namespace,pod) group_left() kube_pod_labels{label_app=~\"$app\"})" },
    { "refId": "D", "editorMode": "code", "format": "table", "instant": true,
      "expr": "<B expr> / sum by (pod) (kube_pod_container_resource_requests{resource=\"memory\"} * on(namespace,pod) group_left() kube_pod_labels{label_app=~\"$app\"})" }
  ],
  "transformations": [
    { "id": "merge", "options": {} },
    { "id": "organize", "options": {
      "excludeByName": { "Time": true },
      "renameByName": { "pod": "Pod", "Value #A": "CPU (cores)", "Value #B": "Memory",
        "Value #C": "CPU % of request", "Value #D": "Memory % of request" } } }
  ],
  "fieldConfig": { "defaults": {}, "overrides": [
    { "matcher": { "id": "byName", "options": "CPU (cores)" }, "properties": [
      { "id": "unit", "value": "short" }, { "id": "decimals", "value": 3 }] },
    { "matcher": { "id": "byName", "options": "Memory" }, "properties": [{ "id": "unit", "value": "bytes" }] },
    { "matcher": { "id": "byRegexp", "options": ".*% of request" }, "properties": [
      { "id": "unit", "value": "percentunit" },
      { "id": "custom.cellOptions", "value": { "type": "color-background" } },
      { "id": "thresholds", "value": { "mode": "absolute", "steps": [
        { "color": "green", "value": null }, { "color": "yellow", "value": 0.7 }, { "color": "red", "value": 1 }] } }] }
  ] },
  "options": { "showHeader": true, "cellHeight": "sm",
    "sortBy": [{ "displayName": "Pod", "desc": false }] }
}
```

## Table: lag, worst first

```json
{
  "type": "table",
  "title": "Consumer Lag",
  "description": "Maximum records waiting to be consumed per topic, highest first. Lag that keeps growing means consumers are not keeping up.",
  "targets": [{
    "editorMode": "code", "format": "table", "instant": true, "refId": "A",
    "expr": "max by (topic) (my_app_consumer_lag_max{job=\"my-app\", app=~\"$app\"}) >= 0"
  }],
  "transformations": [
    { "id": "organize", "options": {
      "excludeByName": { "Time": true },
      "renameByName": { "topic": "Topic", "Value": "Lag (records)" } } },
    { "id": "sortBy", "options": { "fields": {}, "sort": [{ "field": "Lag (records)", "desc": true }] } }
  ],
  "fieldConfig": { "defaults": { "unit": "short" }, "overrides": [] },
  "options": { "showHeader": true, "cellHeight": "sm",
    "sortBy": [{ "displayName": "Lag (records)", "desc": true }] }
}
```

## Text panel: how to read this board

```json
{
  "type": "text",
  "title": "",
  "options": {
    "mode": "markdown",
    "content": "## Reading this board\n\n**Task id** is `<subtopology>_<partition>`.\n\n> A value of `-1` means the metric was not recorded. Those values are filtered out."
  }
}
```

## Row

```json
{ "id": 100, "type": "row", "title": "Throughput", "collapsed": false, "gridPos": { "h": 1, "w": 24, "x": 0, "y": 5 }, "panels": [] }
```
