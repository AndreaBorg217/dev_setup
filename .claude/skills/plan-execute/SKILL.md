---
name: plan-execute
description: Use when the user asks to execute, run, resume, or continue a PLAN.md produced by the planner skill - covers task-DAG dispatch, Sonnet/Haiku subagent selection, and gated stg-then-prod deployment.
---

# Plan Execute

Runs on Sonnet. Reads `PLAN.md` at the repo root as the single source of truth - no prior conversation context is required, including after a `/clear`.

## Step 1 - Load

Read `PLAN.md` at the repo root. If it does not exist, tell the user to run the `planner` skill first and stop. Parse the Parallelism line and every task's ID, Status, Model, Goal, How, Verification, and Dependencies fields.

## Step 2 - Select

Find every task whose Status is `PENDING` and whose Dependencies are all `DONE` (a task with `Dependencies: None` is immediately eligible). These form the next dispatch batch. If two or more eligible tasks appear in the same Parallelism group, dispatch them together.

If a deployment task's Dependencies include a stg task, do not select the prod task until that stg task's Status is `DONE` **and** its Results field records a passed verification. If stg failed and was amended, wait for the amended re-verification to land in Results before treating stg as satisfied.

If no task is eligible and the plan is not fully `DONE`, check for a `BLOCKED` or `FAILED` task - report it and stop. Do not guess a workaround.

## Step 3 - Dispatch

For the selected batch, send one message with one subagent call per task (parallel when the batch has more than one task):

- Use the Model named in the task's Model field (`haiku` or `sonnet`) as the Agent tool's `model` parameter.
- Give the subagent the task's Goal, How, and Verification fields verbatim, plus enough file paths/context from How to act with zero other context.
- Before dispatching, set the task's Status to `IN_PROGRESS` in `PLAN.md`.

## Step 4 - Verify

When a subagent returns, run the task's Verification gate yourself against the artifact it produced (check the exit code, read the file, run the query - whatever the Verification field specifies). Do not accept "looks correct" from the subagent as satisfying verification.

- **Pass** - set Status to `DONE`, write the subagent's deliverable and the verification evidence into Results.
- **Fail on a deployment (stg) task** - amend the failing step per the subagent's findings and re-dispatch that task once. If it fails again, set Status to `FAILED`, write the failure detail into Results, and stop - ask the user for direction rather than retrying indefinitely.
- **Fail on any other task** - set Status to `FAILED`, write the failure detail into Results, and stop - ask the user for direction.

## Step 5 - Gate conclusive operations

Before any commit, push, MR, Slack message, Jira ticket, or other operation that could notify someone outside this session, stop and ask the user for explicit approval, per `rules/safety.md`. Never treat a task's Status as a substitute for that approval, even if the task's How field describes the operation.

## Step 6 - Loop

Repeat Steps 2-5 until every task is `DONE`, or execution halts on a `FAILED`/`BLOCKED` task, or a Manual-section checkbox blocks further progress (announce it and stop). Update `PLAN.md` after every state change - it is the only state that survives a context clear, so partial progress must always be reflected on disk before returning control.

## Step 7 - Report

Once every task is `DONE`, summarize what shipped, cite the Manual-section checklist for any items the user still needs to confirm, and stop.
