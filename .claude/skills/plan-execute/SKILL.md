---
name: plan-execute
description: Use when the user asks to execute, run, resume, or continue a plan produced by the planner skill - covers block-scoped task-DAG dispatch, Sonnet/Haiku subagent selection, forecast-blocker handling, and gated stg-then-prod deployment.
---

# Plan Execute

Runs on Sonnet. Executes exactly one block of a plan per invocation, then stops. Reads the plan directory as the single source of truth - no prior conversation context is required, including after a `/clear`.

## Step 0 - Orchestrator model check

This skill must run on Sonnet. Under `opusplan`, that means running outside plan mode - if the session model is Opus, say so and ask the user to switch before proceeding. The orchestrator's job is dispatch, verification, and `PLAN.md` bookkeeping - it does not implement tasks itself, and it never invokes Opus itself. If a blocker turns out to be architectural, re-invoking `planner` on Opus is the user's call to make, not something this skill does automatically.

Switch to `/ponytail:ponytail ultra` and `/caveman:caveman ultra` to run this skill on Sonnet by sending those exact message

## Step 1 - Load

A **block** is one `>>`-separated segment of the Parallelism line (e.g. `t1 >> [t2, t3] >> t4` is 3 blocks: `t1`, `[t2, t3]`, `t4`). `PLAN.md`'s `## Execution checkpoint` section holds a `Current:` line whose value is either a block number or `COMPLETE`.

Resolve the plan directory: if the user gave an explicit path, use it. Otherwise scan `plans/*/PLAN.md` for exactly one plan whose `Execution checkpoint` section's `Current:` line is not `COMPLETE` - if exactly one qualifies, auto-select it; if zero or more than one qualify, ask the user which plan to run.

From that plan directory, load:

- `PLAN.md` - parse the Parallelism line and its block boundaries, the global constraints, the `Execution checkpoint` section's `Current:` value (the current block number), and every task's ID, Status, Model, Goal, Why, How, Context, Verification, Dependencies, and Results fields.
- `FEATURE_SPEC.md`'s recorded revision/hash and compare it to the revision/hash `PLAN.md` recorded at plan time. A mismatch means the spec drifted since planning - treat this as a stale-spec condition (see Halt conditions) and do not execute against it.
- Only the `CONTEXT.md` findings actually referenced (by finding ID, e.g. `F3`) by the current block's tasks - never load the whole file. Pull each referenced `### F<n>` section's Evidence/Finding/Used by/Valid until-Recheck when.
- Any dependency task's Results that the current block's tasks reference (e.g. a fanout task reusing a probe task's validated adaptation) - pull that content verbatim, do not make the subagent re-derive it.

If `PLAN.md` does not exist at the resolved path, check `~/.claude/plans/` - if a plan exists only there, the `planner` skill did not complete its post-approval materialization step; tell the user to re-run `planner` to finish that step rather than falling back to the staging copy. If no plan exists anywhere, tell the user to run the `planner` skill first and stop.

## Halt conditions {#halt-conditions}

On any of the following, stop immediately and ask the user via `AskUserQuestion` for guidance on how to unblock. Write current state to `PLAN.md` first (Status/Results) so nothing is lost across a clear. Do not retry the failing operation, do not skip the task, do not invent a workaround.

Do not set a task's Status to `BLOCKED` as part of this stop. Present the user with concrete options via `AskUserQuestion` (retry with amendment, skip, abort, or mark BLOCKED) and wait for their answer. Only write `Status: BLOCKED` to `PLAN.md` if the user's answer explicitly says to mark it BLOCKED. Otherwise apply whatever resolution the user chose and resume from Step 2 for the remainder of the current block - never default to `BLOCKED` on an ambiguous or partial answer.

Halt on:

- `PLAN.md` is missing or unparseable (missing required task fields, malformed Parallelism line).
- The Parallelism line is inconsistent with the Dependencies fields, or there is a dependency cycle / a reference to a task ID that does not exist.
- `FEATURE_SPEC.md`'s current revision/hash does not match what `PLAN.md` recorded - the spec is stale relative to the plan.
- No task in the current block is `PENDING`-and-eligible per Step 2, the block is not fully `DONE`, and a scan of the block finds one already `BLOCKED` or `FAILED` - report that task by ID and stop.
- A task's Verification field is unfalsifiable or references an artifact that cannot exist.
- A forecast blocker reaching this skill is architectural (i.e. misclassified as non-material or task-local at planning time) - halt and let the user decide, including whether to re-run `planner` on Opus.
- A subagent errors out, returns nothing, or reports a missing tool/credential/permission.
- A task fails its one automatic repair attempt (see Step 4).
- A Manual-section item blocks further progress.
- A conclusive operation needs approval per Step 5.

The report must name the task ID, the exact failure, and the specific decision needed from the user.

## Step 2 - Select

This skill dispatches **one block, then stops.** Never start a second block in the same invocation.

Within the current block (the one loaded in Step 1), find every task whose Status is `PENDING` and whose Dependencies are all `DONE` (a task with `Dependencies: None` is immediately eligible). These form the next dispatch batch. If two or more eligible tasks appear in the same Parallelism group, dispatch them together.

If a deployment task's Dependencies include a stg task, do not select the prod task until that stg task's Status is `DONE` **and** its Results field records a passed verification. If stg failed and was repaired, wait for the repaired re-verification to land in Results before treating stg as satisfied.

If no task in the current block is eligible and the block is not fully `DONE`, scan the block for one already `BLOCKED` or `FAILED` and see [Halt conditions](#halt-conditions) - report it and stop, do not guess a workaround.

## Step 3 - Dispatch

For the selected batch, send one message with one subagent call per task (parallel when the batch has more than one task):

- Use the Model named in the task's Model field (`haiku` or `sonnet`) as the Agent tool's `model` parameter.
- `subagent_type` per `rules/subagents.md`: prefer `caveman:cavecrew-builder` for a bounded 1-2 file edit task, `caveman:cavecrew-reviewer` for a review/verification-shaped task, `cavecrew-investigator` or `Explore` for a locate/grep task. Fall back to `general-purpose` only when none fit - never default to it.
- Give the subagent the task's Goal, Why, How, and Verification fields verbatim, plus the referenced context findings and dependency Results pulled in Step 1 - enough for it to act with zero other context.
- If two tasks in the same batch would write the same file, dispatch them serially instead of in parallel, per the Parallelism judgement section in `rules/subagents.md`.
- Before dispatching, set the task's Status to `IN_PROGRESS` in `PLAN.md`.
- If a subagent errors out, returns nothing, or reports a missing tool/credential/permission, see [Halt conditions](#halt-conditions).

**Forecast blockers reaching this skill:** `planner` splits forecast blockers by materiality at planning time; only non-material and task-local blockers should ever reach execution.

- **Non-material** - record it in Results and continue; no action needed.
- **Task-local** - amend the task's own contract (Goal/How/Verification wording, not its architecture or dependencies) to account for it, then dispatch as amended.
- **Architectural** - this means the blocker was misclassified at planning time. Do not attempt to absorb it here; see [Halt conditions](#halt-conditions).

**Model discipline:**

- Always pass `model` explicitly on every `Agent` call. `CLAUDE_CODE_SUBAGENT_MODEL: inherit` means an omitted `model` inherits the session model (Sonnet here, but never rely on the default).
- A task's Model field is authoritative for that task's own dispatch.
- When executing a task needs more dispatches than the plan enumerated, the orchestrator chooses their models: `sonnet` for building, editing, and debugging; `haiku` for noisy mechanical commands - test suites, builds, dependency installs, curls/API probes, log greps, polling, doc/README/runbook sync, artifact consistency checks - returning status, the exact command, and only the relevant snippets, not raw output. Same `subagent_type` preference applies to these extra dispatches as to plan-enumerated tasks above.
- Subagents are leaf-tier per `rules/subagents.md`: they must not call `Agent` - enforced by the `no-nested-agents.py` `PreToolUse` hook plus the `general-purpose` agent override, not just this instruction. Any further split happens here, in the orchestrator, never inside a subagent.
- Parallel vs serial for those extra dispatches follows the Parallelism judgement section in `rules/subagents.md` (probe-then-fanout, never two agents writing the same file).
- Do not insert an ad hoc "review this" sub-dispatch beyond what the plan specifies. Generic same-model re-read review is not a substitute for verification - Step 4's falsifiable-check discipline is.

## Step 4 - Verify

When a subagent returns, run the task's Verification gate yourself against the artifact it produced (check the exit code, read the file, run the query - whatever the Verification field specifies). Do not accept "looks correct" from the subagent as satisfying verification. If the Verification field itself is unfalsifiable, see [Halt conditions](#halt-conditions) rather than inventing a substitute check.

- **Pass** - set Status to `DONE`, write the subagent's deliverable and the verification evidence into Results (compacted per Step 6).
- **Fail, any task type** - one automatic repair attempt is allowed, regardless of whether the task is a deployment/stg task or any other type. The repair may not change: the task's goal, its approved behavior, its dependencies, its allowed files, its data contract, its architecture, its validation policy, or the deployment boundary. Amend within those fences per the subagent's findings and re-dispatch once.
  - If the repaired attempt passes, treat it as a normal pass.
  - If it fails again, set Status to `FAILED`, write the failure detail into Results, and stop per [Halt conditions](#halt-conditions) with options to amend/retry/skip/mark BLOCKED/abort. No third automatic repair.
- **Skip the repair and ask immediately** when any of the following is true, rather than attempting an automatic repair: requirements changed, the architecture is invalid, credentials or permissions are missing, the failure carries destructive risk, prod state is uncertain, forbidden files are implicated, a new dependency is required, or the spec is stale.

**Partial parallel-block failure:** when a batch has multiple tasks and only some fail, keep the passing tasks' Status at `DONE` with their evidence retained - do not rerun them. Resolve the failing task per the user's choice from the halt. The block stays current (not advanced) until every task in it is resolved.

## Step 5 - Gate conclusive operations

Unchanged: before any commit, push, MR, Slack message, Jira ticket, or other operation that could notify someone outside this session, stop and ask the user for explicit approval, per `rules/safety.md`. Never treat a task's Status as a substitute for that approval, even if the task's How field describes the operation. This gate applies regardless of block or repair state.

## Step 6 - Checkpoint and stop

Once every task in the current block is resolved (`DONE`, or `BLOCKED`/`FAILED` per an explicit user decision), compact and checkpoint, then stop - do not loop back to Step 2 for the next block. A new invocation of this skill picks up the next block.

Compact once per block, including parallel sub-blocks: a 5-way parallel block yields one checkpoint, not five. Rewrite each resolved task's Results to:

```
Outcome:
Files changed:
Verification:
Reusable findings:
Caveats for next block:
```

No raw logs or long reasoning. The Sonnet orchestrator writes this directly in the normal case. Dispatch a separate Haiku compactor only when the combined output exceeds roughly 4KB, findings overlap across agents, the raw output is noisy, or `CONTEXT.md` is nearing its size limit.

Update the `## Execution checkpoint` section's `Current:` line to the next block's number (or `COMPLETE` if this was the last block), and persist task status, files changed, verification results, reusable findings, and caveats for the next block to `PLAN.md` before returning control - it is the only state that survives a context clear.

## Step 7 - Report

This step fires **only** on the invocation that leaves every task in the entire plan `DONE`. In that case:

> Once every task is `DONE`, reply with 'Done,' citing the Manual-section checklist for any items the user still needs to confirm, and stop.

Every other block-completing invocation stops silently after Step 6 - no summary, no "Done," no report. The user runs this skill again to pick up the next block.
