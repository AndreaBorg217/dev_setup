---
name: plan-execute
description: Use when the user asks to execute, run, resume, or continue a PLAN.md produced by the planner skill - covers task-DAG dispatch, Sonnet/Haiku subagent selection, and gated stg-then-prod deployment.
---

# Plan Execute

Runs on Sonnet. Reads `PLAN.md` at the repo root as the single source of truth - no prior conversation context is required, including after a `/clear`.

## Step 0 - Orchestrator model check

This skill must run on Sonnet. Under `opusplan`, that means running outside plan mode - if the session model is Opus, say so and ask the user to switch before proceeding. The orchestrator's job is dispatch, verification, and `PLAN.md` bookkeeping - it does not implement tasks itself.

## Step 1 - Load

Read `PLAN.md` at `$(git rev-parse --show-toplevel)/PLAN.md`. If it does not exist there, check `~/.claude/plans/` - if a plan exists only there, the `planner` skill did not complete its post-approval materialization step; tell the user to re-run `planner` to finish that step rather than falling back to the staging copy. If no plan exists anywhere, tell the user to run the `planner` skill first and stop. Parse the Parallelism line and every task's ID, Status, Model, Goal, How, Verification, and Dependencies fields.

## Halt conditions {#halt-conditions}

On any of the following, stop immediately and ask the user via `AskUserQuestion` for guidance on how to unblock. Write current state to `PLAN.md` first (Status/Results) so nothing is lost across a clear. Do not retry the failing operation, do not skip the task, do not invent a workaround.

Do not set a task's Status to `BLOCKED` as part of this stop. Present the user with concrete options via `AskUserQuestion` (retry with amendment, skip, abort, or mark BLOCKED) and wait for their answer. Only write `Status: BLOCKED` to `PLAN.md` if the user's answer explicitly says to mark it BLOCKED. Otherwise apply whatever resolution the user chose and resume the loop from Step 2 - never default to `BLOCKED` on an ambiguous or partial answer.

Halt on:

- `PLAN.md` is missing or unparseable (missing required task fields, malformed Parallelism line).
- The Parallelism line is inconsistent with the Dependencies fields, or there is a dependency cycle / a reference to a task ID that does not exist.
- No task is `PENDING`-and-eligible per Step 2, the plan is not fully `DONE`, and a scan of all tasks finds one already `BLOCKED` or `FAILED` - report that task by ID and stop.
- A task's Verification field is unfalsifiable or references an artifact that cannot exist.
- A subagent errors out, returns nothing, or reports a missing tool/credential/permission.
- A task fails its gate per Step 4 (a deployment/stg task after its one amended re-dispatch; any other task on first failure).
- A Manual-section item blocks further progress.
- A conclusive operation needs approval per Step 5.

The report must name the task ID, the exact failure, and the specific decision needed from the user.

## Step 2 - Select

Find every task whose Status is `PENDING` and whose Dependencies are all `DONE` (a task with `Dependencies: None` is immediately eligible). These form the next dispatch batch. If two or more eligible tasks appear in the same Parallelism group, dispatch them together.

If a deployment task's Dependencies include a stg task, do not select the prod task until that stg task's Status is `DONE` **and** its Results field records a passed verification. If stg failed and was amended, wait for the amended re-verification to land in Results before treating stg as satisfied.

If no task is eligible and the plan is not fully `DONE`, scan every task for one already `BLOCKED` or `FAILED` and see [Halt conditions](#halt-conditions) - report it and stop, do not guess a workaround.

## Step 3 - Dispatch

For the selected batch, send one message with one subagent call per task (parallel when the batch has more than one task):

- Use the Model named in the task's Model field (`haiku` or `sonnet`) as the Agent tool's `model` parameter.
- `subagent_type` per `rules/subagents.md`: prefer `cavecrew-builder` for a bounded 1-2 file edit task, `cavecrew-reviewer` for a review/verification-shaped task, `cavecrew-investigator` or `Explore` for a locate/grep task. Fall back to `general-purpose` only when none fit - never default to it.
- Give the subagent the task's Goal, How, and Verification fields verbatim, plus enough file paths/context from How to act with zero other context.
- If a task's How references another task's Results (e.g. a fanout task reusing a probe task's validated adaptation), pull that dependency's actual Results content from `PLAN.md` and paste it into the dispatch prompt verbatim - do not make the subagent re-derive or guess it.
- If two tasks in the same batch would write the same file, dispatch them serially instead of in parallel, per the Parallelism judgement section in `rules/subagents.md`.
- Before dispatching, set the task's Status to `IN_PROGRESS` in `PLAN.md`.
- If a subagent errors out, returns nothing, or reports a missing tool/credential/permission, see [Halt conditions](#halt-conditions).

**Model discipline:**

- Always pass `model` explicitly on every `Agent` call. `CLAUDE_CODE_SUBAGENT_MODEL: inherit` means an omitted `model` inherits the session model (Sonnet here, but never rely on the default).
- A task's Model field is authoritative for that task's own dispatch.
- When executing a task needs more dispatches than the plan enumerated, the orchestrator chooses their models: `sonnet` for building, editing, and debugging; `haiku` for noisy mechanical commands - test suites, builds, dependency installs, curls/API probes, log greps, polling - returning status, the exact command, and only the relevant snippets, not raw output. Same `subagent_type` preference applies to these extra dispatches as to plan-enumerated tasks above.
- Subagents are leaf-tier per `rules/subagents.md`: they must not call `Agent` - enforced by the `no-nested-agents.py` `PreToolUse` hook plus the `general-purpose` agent override, not just this instruction. Any further split happens here, in the orchestrator, never inside a subagent.
- Parallel vs serial for those extra dispatches follows the Parallelism judgement section in `rules/subagents.md` (probe-then-fanout, never two agents writing the same file).

## Step 4 - Verify

When a subagent returns, run the task's Verification gate yourself against the artifact it produced (check the exit code, read the file, run the query - whatever the Verification field specifies). Do not accept "looks correct" from the subagent as satisfying verification. If the Verification field itself is unfalsifiable, see [Halt conditions](#halt-conditions) rather than inventing a substitute check.

- **Pass** - set Status to `DONE`, write the subagent's deliverable and the verification evidence into Results.
- **Fail on a deployment (stg) task** - amend the failing step per the subagent's findings and re-dispatch that task once. If it fails again, set Status to `FAILED`, write the failure detail into Results, and stop per [Halt conditions](#halt-conditions) rather than retrying indefinitely.
- **Fail on any other task** - set Status to `FAILED`, write the failure detail into Results, and stop per [Halt conditions](#halt-conditions).

## Step 5 - Gate conclusive operations

Before any commit, push, MR, Slack message, Jira ticket, or other operation that could notify someone outside this session, stop and ask the user for explicit approval, per `rules/safety.md`. Never treat a task's Status as a substitute for that approval, even if the task's How field describes the operation.

## Step 6 - Loop

Repeat Steps 2-5 until every task is `DONE`, or execution halts on a `FAILED`/`BLOCKED` task, or a Manual-section checkbox blocks further progress (announce the blocking Manual-section item to the user and stop until they confirm it's resolved). Update `PLAN.md` after every state change - it is the only state that survives a context clear, so partial progress must always be reflected on disk before returning control.

## Step 7 - Report

Once every task is `DONE`, reply with 'Done,' citing the Manual-section checklist for any items the user still needs to confirm, and stop.
