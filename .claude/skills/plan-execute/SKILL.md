---
name: plan-execute
description: Use when the user asks to execute, run, resume, or continue a PLAN.md produced by planner - validates the plan, dispatches exactly one execution block, verifies results, and preserves resumable state in PLAN.md.
---

# Plan Execute

Run on Sonnet outside plan mode. Execute exactly one `Blocks:` group per invocation, reply `Done`, and stop. Treat `PLAN.md` as the sole plan and execution state; no prior conversation is required.

## 1. Preflight

This skill must run on Sonnet. If the session model is Opus, reply `Manual step switch to Sonnet required` and stop. Do not prescribe or run plugin commands, and never invoke Opus.

Resolve the plan:

1. Use an explicit user-supplied path when present.
2. Otherwise scan `plans/*/PLAN.md` for plans containing any task whose Status is not `DONE`.
3. If no `PLAN.md` exists, reply `Manual step run planner required`; never execute a harness staging file.
4. Auto-select only when exactly one plan is incomplete. If plans exist but none are incomplete, reply `Done`. If several are incomplete, reply `Manual step choose PLAN.md required`.

If an explicitly selected plan already has every task `DONE`, reply `Done` and stop.

Resolve the repository root, then validate before loading work:

`python3 "$root/.claude/scripts/validate-plan.py" "$plan_file" --phase execution`

On validation failure, reply `Blocked on plan validation: <exact failure>` and stop. From the valid file, load the Objective, Boundaries and decisions, optional Grounded facts and Manual actions, Blocks groups, and every task's Status, Model, Goal, Writes, How, Verification, and Results.

Execute only the approved behavior in the plan. Repository evidence can establish a technical fact but cannot broaden scope or supply a missing user preference.

## 2. Select and recover the current block

The current block is the first `>>`-separated group containing a task whose Status is not `DONE`. Never start a later block and never execute more than one block per invocation.

- Halt when any task in the current block is `FAILED` or `BLOCKED`; name the task and required user decision.
- Recover repository-only `IN_PROGRESS` work by running its Verification first. If it passes, record Results and mark it `DONE`. If it fails, clear Results, set it to `PENDING`, and dispatch it with instructions to inspect and finish the existing partial artifact.
- Do not automatically recover an `IN_PROGRESS` task that may have changed external state or is not idempotent. Ask the user to confirm the external state before retrying.
- Select every `PENDING` task in the current block. Previously `DONE` tasks stay done and are not repeated.

Before dispatch, confirm that bracketed tasks do not overlap in Writes. Reject any git operation, deployment, test-file change, or documentation change not explicitly included under Boundaries and decisions. When an included operation requires approval under `rules/safety.md`, obtain that approval before setting Status to `IN_PROGRESS` or dispatching it. A blocking Manual action also halts before dispatch.

## 3. Dispatch

Set every selected task to `IN_PROGRESS` in `PLAN.md`, then send one message containing one Agent call per task; parallelize a bracketed group.

- Route model, subagent type, and parallelism under `rules/subagents.md`. Pass the task's Model (`haiku` or `sonnet`) explicitly; the plan's value is authoritative.
- Give each subagent the Objective, applicable Boundaries and decisions and Grounded facts, its Goal, Writes, How, Verification, and any earlier task Results referenced by full ID.
- Pass this execution contract with every task:
  - Treat the delegated task as exhaustive. Perform exactly its Goal and How, and write only within Writes.
  - Do not add adjacent fixes, tests, documentation, comments, abstractions, safeguards, dependencies, cleanup, or formatting unless the Objective, boundaries, or task explicitly require them.
  - Obey `rules/safety.md` and complete the stated Verification; narrow scope never permits bypassing either.
  - Do not infer a missing product or design decision and do not ask the user directly. If blocked, make no speculative edit and return the exact blocker to the orchestrator in one sentence.
- Extra dispatches may split already-approved work but may not expand the task. Keep them leaf-tier under `rules/subagents.md`; any further split returns to this orchestrator.

There are no forecast blockers to resolve during execution. `planner` must have resolved them. If execution reveals an architectural issue, multiple valid repairs, or a missing user decision, persist the evidence and halt for plan amendment.

If a subagent errors, returns nothing, or lacks a required tool, credential, or permission, set its Status to `FAILED` and record the exact error. In a parallel batch, first verify and persist every sibling result already returned, then halt. Do not leave a completed or failed task `IN_PROGRESS`.

## 4. Verify and repair

Run each task's Verification against the produced artifact; never accept the subagent's assertion as proof.

- **Pass:** set Status to `DONE` and record compact Results.
- **Fail:** allow one automatic repair only when the failure is ground-truth evidence for exactly one repair already permitted by Goal, Writes, How, Verification, and the global boundaries. Redispatch once and re-verify.
- **Ask instead:** halt immediately when the repair is ambiguous, changes requirements or architecture, adds a dependency, exceeds Writes, affects uncertain external state, requires missing credentials, or contradicts the plan.
- **Second failure:** set Status to `FAILED`, record the failure, and halt. Do not offer or infer a skip; skipping requires amending the plan.

In a parallel block, retain passing tasks as `DONE`. Never rerun them while resolving another task.

Write Results directly in this compact form, omitting empty lines:

```
Outcome:
Files changed:
Verification:
Notes for later tasks:
```

Do not dispatch a compactor and do not store raw logs or long reasoning.

## 5. Finish or halt

When every task in the current block is `DONE`, run execution validation again, reply exactly `Done`, and stop. The next invocation derives the next unfinished block from task statuses; there is no checkpoint field.

On any halt, persist Status and Results when the plan is writable, then reply on one line as `Blocked on <task ID>: <exact problem>` or `Manual step <required action> required`. Do not add a summary or paragraph. Do not mark a task `BLOCKED` unless the user explicitly chooses that state, do not advance past a failed/blocked task, and do not retry an unchanged failing operation.
