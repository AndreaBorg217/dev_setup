# Plan directory artifact skeletons

Literal skeletons `planner` fills in when composing a plan's artifacts under `plans/<kebab-case-name>/`. Copy the relevant structure, replace every `<...>` placeholder, and delete this comment block. `PLAN.md` is the only one of these that `plan-execute` treats as authoritative state.

## PLAN.md

```markdown
# PLAN.md

<One-line headline: the outcome this plan achieves.>

Feature-spec revision: <hash> (rev <N>) - both values as reported by feature-spec at plan time

## Execution Contract
Orchestrator: sonnet. Dispatch each task to a subagent using the Model named
in that task. Any additional sub-dispatch the orchestrator needs beyond a
task's own Model (work the plan didn't itself enumerate) is the
orchestrator's call - sonnet for building and debugging, haiku for noisy
commands. Run tasks within a Parallelism group concurrently, in one
message with multiple tool calls. Do not dispatch a task until every ID in
its Dependencies field has Status DONE. Update each task's Status and
Results fields in this file as work completes, and keep Execution
checkpoint current - this file is the only state that survives a context
clear.

## Objective
<What this plan achieves, in full, self-contained detail.>

## Invariants
- <Property that must remain true throughout execution.>

## Non-goals
- <Explicitly out of scope, so no task drifts into it.>

## Allowed files
- <Paths/globs execution is allowed to touch.>

## Forbidden changes
- <Paths, patterns, or actions execution must never perform.>

## Accepted decisions
- <Design/scope decision made during planning, with brief rationale.>

## Rejected decisions
- <Option considered and rejected, with brief rationale - prevents re-litigating.>

## Validation policy
<How correctness is judged across this plan - test commands, review gates, acceptance thresholds.>

## Deployment boundary
<Which environments are in scope, the stg-then-prod gate, and what requires explicit human approval before it can be triggered.>

## Forecast blockers
<Non-material and task-local blockers carried from planning time, for plan-execute to consume. Architectural-tier blockers were resolved before this file was written and do not appear here unresolved.>

### B1 — Blocker title
- Why it may block:
- Probe:
- Expected outcomes:
- Affected tasks:
- Materiality: non-material | task-local
- Context output:

## Execution checkpoint
<Which block is current or next, updated as execution proceeds - see SKILL.md
Step 7 for what a block is. This field is what lets plan-execute auto-resume
this plan after a session ends mid-execution, without the user having to
specify a path - a plan is "incomplete" as long as this is not COMPLETE.>
Current: <block number, e.g. "1", or "not started" | COMPLETE>

## Tasks
Parallelism: t1 >> [t2, t3] >> t4
<!-- one block per >>-separated segment above, per SKILL.md Step 7 -->

### t1-<kebab-slug>
Status: PENDING
Model: haiku
Goal: <what this task must accomplish, one sentence>
Why: <link back to Objective or an Accepted decision>
How: <concrete steps or commands to reach the goal>
Context: <CONTEXT.md finding IDs this task's executor should read, or None>
Verification: <observable artifact assertion - exit code, file, query result, table - never "looks correct">
Dependencies: None
Results: <blank until executed>

### t2-<kebab-slug>
Status: PENDING
Model: sonnet
Goal:
Why:
How:
Context:
Verification:
Dependencies: t1-<kebab-slug>
Results:

## Deployment

### t<N>-deploy-stg
Status: PENDING
Model: sonnet
Goal: Deploy the change to staging and verify it end to end.
Why: Required gate before prod per Deployment boundary.
How: <runbook expanded from the user's skeleton into concrete commands, one
verification step after each command. On any verification failure, amend
the failing step and re-verify before marking DONE.>
Context: <CONTEXT.md finding IDs, or None>
Verification: All runbook steps pass their individual verification; final
end-to-end check recorded in Results.
Dependencies: <upstream implementation task IDs>
Results:

### t<N+1>-deploy-prod
Status: PENDING
Model: sonnet
Goal: Deploy the verified change to production.
Why: Delivers the objective to production once stg is proven.
How: <the amended runbook that actually passed on stg - not the original skeleton>
Context: <CONTEXT.md finding IDs, or None>
Verification: <same verification steps as stg, run against prod>
Dependencies: t<N>-deploy-stg (blocked until STG Status is DONE with a passed verification in Results)
Results:

## Manual actions
- [ ] <check only the human user can perform - approval, dashboard review, credential handling, anything with an external side effect>
```

## CONTEXT.md

```markdown
# CONTEXT.md

Compact evidence cache. Not a transcript. Reference finding IDs from tasks; never inline whole findings into a task, never copy raw logs/files/secrets here.

## Stable
### F1 — Title
- Evidence:
- Finding:
- Used by:
- Valid until / Recheck when:

## Volatile
### F2 — Title
- Evidence:
- Finding:
- Used by:
- Valid until / Recheck when: <always rechecked before use - never treat as durable>

## Execution discoveries
<Populated by plan-execute as it runs, same F<N> shape.>

## Invalidated
<Findings later disproven or superseded - kept so they aren't rediscovered and re-trusted.>
```

## PLAN.HUMAN.md

Generated by a Haiku dispatch (or written inline for a lightweight plan) from `PLAN.md`'s Objective, task IDs/names, short Why, goals, dependencies, parallelism, and Manual actions only - no repo inspection, no redesign. Not authoritative; checkboxes are updated mechanically as `PLAN.md` changes.

```markdown
# <Plan title>

## Objective
<Same objective as PLAN.md, in plain language.>

## Work checklist
- [ ] **t1 — <Task short title>**
  <One or two sentences: why it exists, what will be done, dependency.>
- [ ] **t2 — <Task short title>**
  <One or two sentences.>

## Parallelism
`t1 >> [t2, t3] >> t4`

## Developer actions
- [ ] <Required action from PLAN.md's Manual actions section.>
```
