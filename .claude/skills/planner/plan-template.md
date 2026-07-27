# PLAN.md skeleton

Literal skeleton `planner` fills in when composing `PLAN.md`. Copy this structure, replace every `<...>` placeholder, and delete this comment block.

```markdown
# PLAN.md

<One-line headline: the outcome this plan achieves.>

## Execution Contract
Orchestrator: sonnet. Dispatch each task to a subagent using the Model named
in that task. Run tasks within a Parallelism group concurrently, in one
message with multiple tool calls. Do not dispatch a task until every ID in
its Dependencies field has Status DONE. Update each task's Status and
Results fields in this file as work completes - this file is the only
state that survives a context clear.

## Tasks
Parallelism: t1 >> [t2, t3] >> t4

### Task 1 - <short title>
**ID:** t1-<kebab-slug>
**Status:** PENDING
**Model:** `haiku`
**Goal:** <what this task must accomplish, one sentence>
**How:** <concrete steps or commands to reach the goal>
**Verification:** <observable artifact assertion - exit code, file, query result, table - never "looks correct">
**Dependencies:** None
**Results:** <blank until executed>

### Task 2 - <short title>
**ID:** t2-<kebab-slug>
**Status:** PENDING
**Model:** `sonnet`
**Goal:**
**How:**
**Verification:**
**Dependencies:** t1-<kebab-slug>
**Results:**

## Deployment

### Task N - Deploy to STG
**ID:** t<N>-deploy-stg
**Status:** PENDING
**Model:** `sonnet`
**Goal:** Deploy the change to staging and verify it end to end.
**How:** <runbook expanded from the user's skeleton into concrete commands,
one verification step after each command. On any verification failure,
amend the failing step and re-verify before marking DONE.>
**Verification:** All runbook steps pass their individual verification; final
end-to-end check recorded in Results.
**Dependencies:** <upstream implementation task IDs>
**Results:**

### Task N+1 - Deploy to PROD
**ID:** t<N+1>-deploy-prod
**Status:** PENDING
**Model:** `sonnet`
**Goal:** Deploy the verified change to production.
**How:** <the amended runbook that actually passed on stg - not the original skeleton>
**Verification:** <same verification steps as stg, run against prod>
**Dependencies:** t<N>-deploy-stg (blocked until STG Status is DONE with a passed verification in Results)
**Results:**

## Manual
- [ ] <check only the human user can perform - approval, dashboard review, credential handling, anything with an external side effect>
```
