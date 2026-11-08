# Dashboard pattern

House conventions for Prometheus dashboards. Lines marked "Improvement" are deliberate upgrades on common practice.

## Principles

The aim is a dashboard that stays readable on every visit. Show what can fail and what needs optimising, and nothing else.

- Every panel is a failure signal (F) or an optimisation signal (O). Drop panels that are neither, except the explanatory text panel and inventory tables. Keep only what answers: is it alive, is it keeping up, where is the lag, is memory and disk safe.
- Colour means something. Series are quiet: thin lines, 10% fill, no points (bars excepted). Colour is reserved for state, such as stat backgrounds and ratio-of-request cells.
- Thresholds exist only where a bound exists: utilisation (yellow at 0.7, red at 0.9-1), error counts (red at 1), enum states. Remove the default red-at-80 step Grafana adds to new panels.
- Gaps show as gaps (`spanNulls=false`), because a gap is a signal. Use `true` only on sparse gauges.
- Scope is baked in. Namespace, workload and job sit in every variable and selector. There is no free job or source selector, so a viewer cannot pick the wrong environment.
- Worst first: lag, top N and failure lists sort descending (see Sorting).
- Empty panels explain themselves (see Empty and N/A handling).
- Prefer a few dense stats over tall charts for "current value" questions. Pick each panel's visual by the question it answers (see Visual type).
- Descriptions carry the explanation, so the layout need not hide detail.

## Visual type

Choose the visual by the question the panel answers. A wrong type is the most common reason a panel is misread or ignored.

| Question | Visual | Key options | Reference (uid #id) |
|---|---|---|---|
| Is it fine right now? Enum state | stat | value map, `colorMode=background`, `graphMode=none`, `lastNotNull` | `streams_summary_v2` #50 |
| Is it fine right now? Latency or rate with its trend | stat | `graphMode=area`, `colorMode=value`, green only, `lastNotNull` | `streams_summary_v2` #4 (pair), #9 (rate) |
| Is it keeping up? Ratio with a healthy bound | stat | `colorMode=background`, thresholds at the bound, `decimals=2` | `streams_summary_v2` #52 |
| Where is the time or load going right now? Shares of a whole | stat (instant per part) beside a stacked timeseries | `textMode=value_and_name`, `percentunit`, `colorMode=background` | `streams_thread_v2` #3 with #2 |
| Is any entity far from the rest? Skew | stat (min and max) beside a timeseries | two instant targets, `textMode=value_and_name` | `streams_task_v2` #16 with #20 |
| How is it trending? Rate, latency, ratio, memory over time | timeseries, lines | `drawStyle=line`, `lineWidth=1` (2 for a hero chart), `fillOpacity=10`, `showPoints=never`, `stacking=none`, `min: 0` | `streams_thread_v2` #6, `streams_producers_consumers_v2` #8 |
| How many events happened over time, and how many failed? Counts per bucket split by outcome | timeseries, bars | `drawStyle=bars`, `fillOpacity=80`, one target per outcome, legend and tooltip as in Legends and tooltips. `stacking=none` keeps each outcome its own bar so a small failed count stays visible. Use `stacking=normal` when the total matters more than comparing outcomes | none live, see Recurring panels |
| Who is biggest or worst right now? Ranked current values | bargauge | horizontal, `displayMode=basic`, `valueMode=color`, `showUnfilled=true`, sorted descending | `streams_summary_v2` #18 |
| How does each category compare over the period? Entity by entity | barchart | vertical, `fillOpacity=80`, legend hidden, `reduce` then `organize` then `sortBy` desc | `streams_topic_v2` #18 |
| Which entity needs attention? Several measures per entity, such as usage against requests, lag per topic, an inventory | table | instant, `format=table`, one target per column, `merge` then `organize` to rename to short Title Case columns, colour only on ratio columns, worst first | `streams_producers_consumers_v2` #16, `jvm-overview` #9 |
| How to read this board | text | markdown, only on table-only boards | none |

- Use bars for discrete events per bucket and lines for continuous measures.
- Do not use a timeseries to compare entities at one moment. Use a bargauge or table.
- Do not use a stat for a trend. Use a timeseries, or a stat with a sparkline for rates.
- Detail for the event-count panels and the usage table is under Recurring panels.

Stat KPI patterns. All use instant queries, `lastNotNull`, `justifyMode=center`, a unit and a description. Size is `h=4`; `w` is shown.

| Pattern | Use when | Not when | PromQL shape | Options | w |
|---|---|---|---|---|---|
| Enum state | The metric is a small integer lifecycle code | The number is a measure | `max(<state gauge>)` | value map text and colour per code; thresholds red 0, green 2, orange 3 only where the codes order that way; `colorMode=background`, `graphMode=none` | 2-4 |
| Latency pair | A library publishes avg and max of one operation | Only one of the two exists, then use a single stat | one target each: `avg(<m>_avg >= 0)`, `max(<m>_max >= 0)`, legends `Avg` and `Max` | `unit=ms`, `orientation=horizontal`, `textMode=value`, `graphMode=area`, green only | 4 |
| Rate with sparkline | One throughput number whose trend matters | A count over the range, use `graphMode=none` | `sum(<rate gauge>)` or `sum(rate(<counter>[5m]))` | `unit=ops`, `graphMode=area`, `colorMode=value`, green only | 4-8 |
| Ratio with health bound | A ratio has a known healthy side (1.0 for keeping up) | There is no bound, then use a plain stat | `sum(<a>) / sum(rate(<b>[5m]))`, guard with `/ (b > 0)` | `unit=short`, `decimals=2`, `colorMode=background`, thresholds red 0, yellow 0.5, green 1 | 4 |
| Breakdown | Parts should sum to a whole (time split, outcome share) | Parts do not share a denominator | one instant target per part, legend per part | `unit=percentunit`, `textMode=value_and_name`, `orientation=horizontal`, `colorMode=background`, `graphMode=none`; pair with a `stacking=normal` timeseries | 8-12 |
| Min and max range | Skew between entities matters more than the mean | Entities are not comparable | `min by (<dim>) (<m>)` and `max by (<dim>) (<m>)`, instant, legends `Min` and `Max` | `textMode=value_and_name`, `orientation=horizontal`, unit as the series; pair with the trend timeseries | 4-8 |

- Pair a breakdown or range stat with its timeseries on the same row: the stat gives the current split, the series gives history. Place the stat left (`w=4-8`) and the timeseries right.

## Suite shape

- One dashboard per altitude, ordered by a numeric prefix in the title and filename: `00` fleet overview, then inventory, traffic, per-task or per-entity detail, saturation, runtime (JVM, pod), and an optional oncall board.
- Titles are 1-5 words, `<Tech> <Altitude>`. Tags are 2-3 and consistent: technology, sub-technology, team.
- Drill down through chained variables, not data links.
- File path: `<Team>/<Technology>/<Subtechnology>/NN_<name>.json`.

## Layout

Grid is 24 columns wide.

Row order, general to specific:

`Overview -> Throughput -> Load Distribution -> Latency -> Health or State -> Resources -> Detail`

- Rows are open, Title Case, 1-4 plain nouns. No units or resource names in row titles.
- Boards under about 10 panels need no rows.
- The first band is 4-10 KPI stats at `h=4` covering health, throughput, latency and errors. A second stat band (rates, ratios) may follow.
- Body rows hold 2-3 timeseries at `h=7-8`. Use `w=12` x2 or `w=8` x3, and `w=24` for one hero chart.
- A wide timeseries (`w=16-18`) may sit beside a stat or bargauge (`w=6-8`) that shows the current value.
- Inside a row, order left to right: totals and rates, latency, ratios and utilisation.
- Tables are `w=24`, `h=8-11`. Barcharts are `w=24`, `h=12`. Bargauges are `h=7-9`.
- Inventory boards that are all tables start with a `w=24`, `h=5` text panel explaining how to read them.

## Variables

- Prometheus `query` variables of the form `label_values(<anchor>{<static scope>, <parent>=~"$parent"}, <label>)`.
- Chain order, general to specific: application -> instance -> thread or worker -> task -> partition -> node, store or topic. Each child filters on its parents. Use `${var}` braces when a variable sits inside a longer regex.
- Anchor on a low-cardinality gauge that exists at that level, so only real values are offered.
- Bake the static scope (namespace, workload, job) into every variable and every panel selector. Never offer "all jobs".
- Settings: `includeAll=true`, explicit `allValue` of `.*` (`.+` when empty must not match), `refresh=1`, `sort: 0` for chain parents, `sort: 3` (natural) for numeric-looking ids such as task, partition and topic, `sort: 1` (alphabetical) for names. `multi=true` only for topic-like leaves and hidden plumbing variables.
- Plumbing variables (instance, thread) are `hide: 2` with no label. Visible ones have Title Case labels. Names are lowercase snake_case matching the label.
- A composite id such as `<a>_<b>` can feed two variables from one label using regex capture groups. Panels rebuild it with `"${a}_${b}"`.
- A `custom` classifier variable (All / External / Internal as `Name : regex`) can feed another variable's `regex` field.
- Improvement: add a `datasource` variable (`type: datasource`, `query: prometheus`) and reference `${datasource}` on every panel, target and variable. A hard-coded UID binds a dashboard to one environment.

## Metric selection

Choose by section. Health and saturation first, then rate, latency, then detail.

| Section | What to show |
|---|---|
| Health | state or up gauge (enum), failure and restart counters, rebalance or reconnect totals |
| Throughput | per-second rate of processed, consumed, produced records and bytes |
| Latency | average and maximum pair per operation, end-to-end where exposed |
| State or saturation | utilisation ratios, cache or queue usage against capacity, backlog or lag |
| Errors | error and dead-letter counters, with a zero fallback on timeseries |
| Resources | memory used against max and committed, threads, GC time, CPU, pod restarts |

Prefer a metric that answers "is it healthy" over one that is merely available. If a library publishes pre-computed avg, max, rate or ratio gauges, use them directly instead of rebuilding them.

## PromQL shapes

- Every selector carries the static scope plus the variable filters: `metric{job="x", app=~"$app"}`. No unscoped queries.
- Counters: `sum by (<dim>) (rate(<counter>[5m]))` for rates and `sum(increase(<counter>[5m]))` for event counts. A fixed 5m window reads the same at every zoom level, so state it in the legend where it matters (`/ 5m`). It hides spikes shorter than the window. Use `$__rate_interval` only as a deviation that the outline step calls out.
- "Over the selected period" stats use `[$__range]`.
- Pre-computed gauges: `avg(<m>)` for averages and ratios, `max(<m>)` for worst case, `sum(<m>)` for rate gauges. A latency panel pairs `avg` and `max` of the same family as two targets with legends `Avg` and `Max`.
- Container metrics carry `container!="",container!="POD"` to drop pause and aggregate series. Enumeration labels carry `<label>=~".+"` to drop series where the label is unset.
- Division guard: `a / (b > 0)`.
- Cardinality count: `count(group by (<dims>) (<metric>))`.
- Restrict one metric family to the selection of another: `<metric> and on(pod) <anchor>`.
- Add a missing label without changing the value: `<metric> + on(job,instance) group_left(<label>) (0 * <anchor>{<label>=~"$x"})`.
- Top N on a bargauge: `sort_desc(sum by (<dim>) (max_over_time(<m>[$__range])))`.
- Instant queries (`instant: true`) for stat, bargauge and table. Range queries for timeseries. `editorMode: "code"` on every target.

## Sorting

- Every panel that ranks or lists entities at one moment (bargauge, barchart, worst-first table) is sorted descending, in both places: `sort_desc(...)` in the query where PromQL allows it, and a `sortBy` transformation with `desc: true`. Grafana honours the transformation, so never rely on the query alone.
- Worst-first or biggest-first is descending: lag, top N, failed-thread lists, throughput rankings. Multi-series timeseries tooltips use `mode=multi` with `sort=desc`, so the largest value is listed first.
- Identity or inventory tables (pod, thread) sort ascending by their key column. Time series are not sorted.
- Table: `options.sortBy` on the renamed column header (`[{"displayName": "Lag (records)", "desc": true}]`), not the raw field name. For a worst-first table add the `sortBy` transformation as well.
- Bargauge and barchart: `sort_desc(...)` in the query plus a `sortBy` transformation with `desc: true` as the last step, so query order and display order agree. A barchart on an instant query adds `seriesToRows` before `sortBy`.
- Known gap: of the reference panels only `streams_summary_v2` #18 and `streams_topic_v2` #18 are sorted descending. The tables (`streams_producers_consumers_v2` #16, `jvm-overview` #9) and the timeseries tooltips (`sort=none`) do not yet follow this rule. Build new panels to the rule, not to the live panels.
- Variable sort values are under Variables.

## Empty and N/A handling

Fix in this order:

1. In the query. `>= 0` drops the `-1` "not recorded" sentinel and NaN. `<= +Inf` drops NaN from empty windows on ratio gauges. `<expr> or vector(0)` gives optional counters (errors, dead-letter writes) a flat zero. `<expr> or label_replace(0 * absent(<expr>), "pod", "none", "", "")` gives a named zero series, so the legend is not empty when nothing happened.
2. `noValue` text on legitimately empty optional metrics, stating the reason, for example "No data (requires DEBUG metrics)". Never `0`.
3. A value mapping `special nan -> "0"` only where NaN still reaches a table cell.

- Counters that always exist get no zero-fill.
- Zero-fill timeseries only. Stats and bargauges rely on `noValue`.
- Do not use `nullValueMode`, null-handling transformations or null overrides.

## Recurring panels

JSON for each is in `examples.md`.

- Event counts (rebalances, failed rebalances, restarts, exceptions): a period KPI stat with `sum(increase(<counter>[$__range]))`, plus a bar timeseries (see Visual type) with one target per outcome (successful, failed) of `sum by (<dim>) (increase(<counter>[5m]))`. Legends state the window (`{{app}} | failed / 5m`). Legend and tooltip as for event-count series under Legends and tooltips. Counters that always exist, such as the successful and failed rebalance counters of a Kafka client, get no zero-fill.
- Usage against requests (resource board): one table of instant targets merged on pod, showing CPU, memory, CPU % of request and memory % of request. Every operand is joined to the selected app and container metrics carry the container filters. Ratio columns use `percentunit` with `color-background` at 0.7 yellow and 1 red. Absolute columns carry a per-column unit override (`short` cores, `bytes`) and no colour. Sort by pod ascending, as an identity table. The ratio uses requests. Limits appear only as dashed series on timeseries.
- Lag table: instant `max by (topic) (<lag>)` with the `>= 0` guard, columns renamed to "Topic" and "Lag (records)", sorted descending through both `options.sortBy` and a `sortBy` transformation. Map NaN to 0 only if it still reaches a cell.

## Panel options

Not used: gauge, state-timeline, pie chart. Heatmap only when the source exposes histogram buckets.

- Stat thresholds: a single green step by default, plus the bounds listed in Principles. Enum states use value mappings with text and colour. A ratio with a healthy bound steps up to it (red 0, yellow 0.5, green 1) with `colorMode=background`.
- Bargauge size is `w=12`, `h=9`. Barchart is `w=24`, `h=12`. Table sizes are under Layout. Stat sizes are in the stat table under Visual type.
- Timeseries that mix external and internal series (for example internal topics) style the internal ones through a `byRegexp` override with a dashed `lineStyle` and lower `fillOpacity`, as for limits.
- Timeseries on utilisation set `max: 1` with orange at 0.8 and red at 0.95. Series that show a limit, capacity or request get a dashed `lineStyle` and lower `fillOpacity` through a `byRegexp` override.
- Stack (`normal`) only for share-of-total charts such as a time breakdown (see Visual type for event counts).
- Set a unit on every panel (`ops`, `ms`, `s`, `percentunit`, `bytes`, `binBps`, `short`). Set `min: 0` on `percentunit`. Use one unit for all rates (`ops`), not a mix of `msgs`, `mps` and `/sec` (`/sec` is not a Grafana unit id).
- Timeseries keep `thresholdsStyle=off` with a single green step. Show threshold lines or areas only on bounded ratios and error rates.
- Colour: `palette-classic` for series, `thresholds` for stats.

## Legends and tooltips

- Multi-series timeseries: right-hand table legend with `mean`, `max` and `lastNotNull`. Narrow `w=8` charts use a bottom list or a bottom table with `lastNotNull` only.
- Bargauge and barchart: bottom list legend or hidden when the bar name is shown.
- Event-count series use legend calc `sum` and tooltip `hideZeros=true`, so idle series are not listed.
- Tooltip: `single` by default. `multi` with `sort=desc` on every multi-series timeseries, so the largest value is listed first. Barchart uses `single`.
- Share-of-total timeseries (time split, `stacking=normal`): right table legend with `mean` and `lastNotNull`. The description states the total ("should sum to about 1.0").
- Skew trend timeseries beside a min and max stat: right table legend with `mean`, `max` and `lastNotNull`.
- Shared crosshair (`graphTooltip=1`) on runtime and oncall boards only.
- `legendFormat` is always set:
  - one dimension: `{{topic}}`
  - entity path: `{{a}} | {{b}}`
  - qualifier: `{{a}} ({{b}})`, or a suffix such as `{{store}} usage`, `limit`, `request`
  - fixed single series: one lowercase noun, or `Avg` and `Max`

## Descriptions

- Every panel has a `description` of 1-2 plain sentences, no markdown or bullets.
- Template: `<Current|Average|Cumulative|Rate> <what is measured> <scope or aggregation>. <How to read it: what a high or low value means, or what a spike implies>.`
- Add a caveat when relevant: needs a recording level, sentinel values are filtered, window length.
- Name the signal to watch. A ratio stat states its bound ("below 1.0 means falling behind"). A breakdown or share series states its total ("should sum to about 1.0"). A ratio in `percentunit` states what 100% means ("100% means no compression"). A skew stat says which gap matters. A ranking says its order ("highest first").
- Timeseries override styling (dashed internal or limit series) needs one description clause saying what the dashed lines are.
- Dashboard `description`: one sentence of purpose. Always add it.
- Row descriptions and panel links are not used.

## Metadata

- `editable: true`, built-in annotations only, `schemaVersion` current, default range `now-1h` to `now`.
- Refresh follows purpose: 2s-5s live debugging, 10s-15s runtime and oncall boards, 1m overview.
- `uid` is a readable snake_case slug derived from the title, for example `<tech>_<area>_overview`. Do not use a random string.
- `timepicker.refresh_intervals` includes the chosen refresh.

## Checklist

- One dashboard per altitude, numbered, 2-3 tags, dashboard description set.
- `${datasource}` variable used on panel, target and variable.
- KPI stat band first, then open Title Case rows in the order above.
- Chained variables with static scope, `includeAll`, `allValue`, `refresh=1`, plumbing hidden.
- Every selector scoped. Rates use a fixed `[5m]` window. Sentinels filtered. Optional counters on timeseries have `or vector(0)`.
- Visual type chosen from the Visual type table. Every panel tagged F or O in the outline. Rankings and worst-first tables sorted descending by query and by `sortBy` transformation, multi-series tooltips `sort=desc`. Thresholds only where a bound exists.
- Stat, timeseries, legend and tooltip options as above. Unit and `legendFormat` on every panel.
- Description on every panel. `noValue` where empty is possible.
- Widths per row sum to 24 and nothing overlaps.
