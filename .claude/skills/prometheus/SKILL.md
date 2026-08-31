---
name: prometheus
description: Use when querying Prometheus for metrics — instant/range queries, PromQL, or discovering metric/label names.
---

# Prometheus

Load this skill once before the first Prometheus query in a task. Keep its instructions active for the rest of that task.

## Establish the base URL

Prometheus's base URL is never hardcoded here. If it isn't already known from the current conversation or environment, ask the user for it before running any query. Do not guess a host from unrelated context.

## Use the reference

Read [references/prometheus-api.md](references/prometheus-api.md) before building a query. It covers the HTTP API endpoints, PromQL basics, and time-range construction with safe, generic examples.

## Query workflow

1. Confirm the base URL.
2. If the exact metric or label name isn't known, discover it first via `/api/v1/label/__name__/values` or `/api/v1/label/<name>/values` rather than guessing.
3. Pick instant query (`/api/v1/query`) for a single point in time, or range query (`/api/v1/query_range`) for a series over a window.
4. Set a request timeout on every call; Prometheus can be slow on wide time ranges or high-cardinality queries.
5. Parse the JSON response (`jq` or `python3 -m json.tool`) rather than eyeballing raw output.

## Keep it generic

Do not write company names, internal hostnames, ticket keys, usernames, or internal topic/service names into this skill or its reference file. Use placeholder hosts (e.g. `$PROMETHEUS_URL`, `prometheus.example.com`) and generic metric names (e.g. `up`, `http_requests_total`) in any example added here.

## Scope

This skill covers read-only querying only. It does not cover Prometheus admin endpoints (snapshot, delete series, config reload) or Alertmanager.
