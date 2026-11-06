---
name: grafana-dashboard-builder
description: Use when designing or building a new Grafana dashboard for a resource from a Prometheus metrics source, before choosing panels, queries or layout, or when fixing a broken panel on an existing dashboard.
when_to_use: "fix panel, broken panel, wrong query, No data, flat zero, panel screenshot, existing dashboard, new Grafana dashboard, scaffold dashboard, panel layout, KPI stat band, chained variables, panel description, metric inventory, missing metric, add an exporter, JMX exporter, kube-state-metrics, instrumentation gap"
---

# Grafana Dashboard Builder

Load this skill once before designing a dashboard. Keep it active for the rest of the task.

Two modes. Build (Steps 1 to 5): input is a resource (service, workload, pipeline, datastore) and a Prometheus metrics source; output is a dashboard JSON file in the house style, written locally. Fix (last section): input is an existing dashboard and a broken panel. Load the `prometheus` skill before the first query. It owns the base URL, auth, discovery endpoints and query safety. This skill owns what to build from the results.

Read these siblings at the step that names them (`pattern.md` at the start of Step 2, `examples.md` at Step 5):

- `references/pattern.md` - how dashboards are organised and styled (layout, variables, PromQL shapes, panel options, legends, descriptions, metadata).
- `references/examples.md` - generic panel and variable JSON to adapt.

## Guardrails

- Write dashboard JSON to a local file first. Reading through the Grafana API is allowed. Writing to Grafana (importing a new dashboard, or overwriting one with `POST /api/dashboards/db`) is allowed only after showing the user the JSON diff and getting explicit approval for each change.
- Grafana credentials come only from the 1Password CLI (`1password-cli` skill): `op run` with placeholder env vars `GRAFANA_URL` and `GRAFANA_TOKEN` and `op://` references. Never print a token.
- Never put real datasource UIDs, hostnames, URLs, tokens, tenant, customer or topic names in the output. Use `${datasource}` and placeholders.
- Do not copy panels, titles or descriptions from existing internal dashboards. Take structure and conventions only.
- Do not run `WebSearch` or `WebFetch` in the main thread. Route external research through `explorer` (Step 3).
- Wait for approval of the outline (Step 4) before generating JSON.

## Step 1 - Ask

Ask these in order, one per turn. Use `AskUserQuestion` for items 3 and 4.

1. Resource: what is it, what does it do, and what does a healthy one look like?
2. Metrics source: which Prometheus (environment, job, namespace, scrape labels). Confirm the base URL through the `prometheus` skill. Do not print credentials.
3. Purpose: live debugging, overview, or oncall. This sets the refresh rate and panel density (see `pattern.md`, Metadata).
4. Scope: one dashboard, or a numbered suite by altitude (fleet overview -> detail).
5. Output path for the JSON file. Default to the current directory.

## Step 2 - Gather

Read `references/pattern.md` first. Then build a metric inventory with the `prometheus` skill. Keep raw output in the sandbox (`ctx_execute`) and keep only the inventory.

1. List metric names for the resource's prefix and exporter. Record type (counter, gauge, histogram, summary) from the metadata endpoint.
2. For each candidate family, record its labels and whether series exist now.
3. Pick a low-cardinality, always-present anchor metric for the variable chain (`pattern.md`, Variables).
4. Map the families to dashboard sections: health, throughput, latency, state or saturation, errors, resources. Mark each wanted measure as present, absent, or present but empty. Tag each as F (can fail: state, errors, lag, restarts, rebalances, saturation) or O (needs optimising: usage against requests, latency tails, top N).

## Step 3 - Close metric gaps

Skip when nothing is absent.

For each absent measure that matters to a healthy-or-not judgement, dispatch `explorer` (`subagent_type: explorer`, `model: haiku`) to research how to expose it. Give it the resource, its version if known, the missing measure, and ask for: the exporter or built-in option, how to enable it, the metric names it adds, and the source URL. Cap its receipt at 1,500 characters.

Present the result to the dev as a proposal, one per gap:

- built-in flag or recording level on the resource itself
- JMX exporter, sidecar or standalone exporter
- an existing platform exporter (kube-state-metrics, node or cAdvisor metrics)
- instrumentation added to the application code

Ask whether to include the affected panels anyway. If yes, add them with a `noValue` text naming the missing exporter. If no, leave them out and list them under "Pending metrics" in the final report.

## Step 4 - Propose the outline

Show a compact outline and wait for approval:

- dashboard title, uid, tags, refresh, default range
- variables in chain order
- rows in order, and under each row the panels as `title | F or O | type | unit | one-line query intent`, with each type chosen from the Visual type table in `pattern.md`
- coverage check: the outline has both F and O panels, and drops any panel that is neither, except the text panel and inventory tables
- pending metrics and any deviations from `pattern.md`

## Step 5 - Execute

1. Read `references/examples.md`.
2. Run every planned query through the `prometheus` skill with the variable values substituted. A panel whose query returns no series gets a `noValue` explanation or is dropped, never shipped silently empty.
3. Generate the JSON. Set `description`, `unit`, `legendFormat` and `datasource` on every panel.
4. Check the file before reporting: valid JSON, unique panel ids, no overlapping `gridPos`, widths per row sum to 24, every panel has a description and unit, every selector carries the static scope, lists are sorted worst-first, and empty-data handling follows `pattern.md`.
5. Write the file to the agreed path.

Report: file path, panel and row counts, queries that returned no data, and the Pending metrics list. Offer to import the JSON through the approval-gated write described in Guardrails and Fix Step 4, or leave it for the dev's normal Grafana review process.

## Fix a panel

Use when a panel on an existing dashboard shows "No data", a flat zero or a wrong value. Inputs: the dashboard from the Grafana API and the user's screenshots.

### Fix Step 1 - Fetch

Run curl inside `op run` so the token stays in the subprocess and masked:

```bash
# env file: GRAFANA_URL=op://<vault>/<item>/url  GRAFANA_TOKEN=op://<vault>/<item>/token
op run --env-file <env-file> -- sh -c \
  'curl -sS -H "Authorization: Bearer $GRAFANA_TOKEN" "$GRAFANA_URL/api/search?type=dash-db&query=<words>"'
```

1. Find the uid with `GET /api/search`, then fetch `GET /api/dashboards/uid/<uid>`. Keep `.dashboard` and its `version`. Save a local copy and work on that.
2. Extract the broken panel with `jq` in `ctx_execute` (panels inside collapsed rows sit in the row panel's `panels`). Keep only that panel and the variables.

### Fix Step 2 - Diagnose

Stop at the first cause that explains the screenshot.

1. Screenshot: panel title, time range, variable values, and whether it shows "No data", zero or a wrong shape.
2. Panel JSON: datasource, each `expr`, `instant` vs range, `format`, transformations, reduce calculation, unit, overrides, `noValue`.
3. Variables: substitute the current values into each `expr`. An empty variable, `All` without `allValue`, or a stale label value is a common cause.
4. Run each substituted query through the `prometheus` skill over the screenshot's range. Query returns data but the panel does not: the fault is presentation (transformation, reduce, unit, override, `instant` on a time series). Query returns nothing: drop matchers and aggregations one at a time until series appear.

Common "No data" causes: metric or label renamed or job no longer scraped; variable resolves to a value with no series; rate window too short; wrong or variable-driven datasource; time range outside retention; division by an absent series; `increase` over a window with no samples.

Rate pitfalls:

- `rate(x[1m])` against a 60 s scrape holds one sample and returns nothing. Use `$__rate_interval`, which is at least four scrape intervals only when the datasource scrape interval setting is correct. Fix that setting or the panel minimum interval, not the window by guesswork.
- Apply `rate` before `sum`. Never `rate` a gauge. Use `irate` only on short, zoomed-in graphs.
- Do not hide empty results with `or vector(0)`. It turns a broken query into a flat zero. Use `noValue` where empty is legitimate.

### Fix Step 3 - Propose

Change the smallest thing that fixes the cause. Do not restyle or reorder unrelated panels. Test the corrected query through the `prometheus` skill, apply `pattern.md` conventions to anything changed or added, write the edited model locally, and show the user a JSON diff (`diff <(jq -S . before.json) <(jq -S . after.json)`) with the tested result.

### Fix Step 4 - Write back (approval-gated)

Only after explicit approval of that diff. One approval covers one change.

1. Re-fetch the dashboard and confirm `version` still matches the one you edited from. If it moved, stop and re-diff.
2. `POST /api/dashboards/db` through `op run` with `{"dashboard": <model, uid and version unchanged>, "overwrite": true, "message": "<what and why>"}`.
3. Report the status and new version only, and ask the dev to reload and confirm or send a new screenshot.

If the dashboard is provisioned from files or a repository, an API write is lost at the next sync. Say so and hand the edited JSON to the dev to apply through their source of truth instead.
