---
name: plan-execute
description: Use when the user asks to execute, run, resume, or continue a plan bundle produced by planner. Dispatches approved tasks and checkpoints resumable state without implementing in the parent.
model: sonnet
disable-model-invocation: true
---

# Plan Execute

Run on Sonnet outside plan mode as an orchestrator. Parse state, enforce scope,
dispatch workers, evaluate compact receipts, and update task files. Do not
inspect source, implement, diagnose, repair, or run verification in the parent.

Schema 4 uses immutable `PLAN.md` context and mutable `tasks/<id>.md` files.
Read schemas 2 and 3, but require amendment rather than inventing missing skill
context, materialization, or handoffs.

## Preflight

- If running on Opus, reply `Manual step switch to Sonnet required` and stop.
- Resolve an explicit plan path first. Otherwise select it only when exactly one
  `plans/*/PLAN.md` is incomplete; report the exact manual step for zero,
  multiple, or already-complete candidates.
- Before the first implementation block, invoke the `git` skill and compare the
  repository to each recorded baseline. Fetch the recorded ref. Ask and stop if
  it advanced or synchronization would require a mutation. On later invocations,
  verify the baseline and completed handoffs without fetching through plan edits.
- Read the selected manifest once. Validate its task index against `Blocks:` and
  task paths, collect statuses with one bounded search, and select only the first
  unfinished block. Read a task only when its block becomes current.
- Read the [task template](../planner/task-template.md) once as the canonical
  task and result schema. Reject malformed tasks, unresolved decisions,
  assumptions, doubts, placeholders, undeclared scope, unjustified model
  selection, incomplete handoffs, or broad local verification. Do not fill a
  planning gap during execution. Legacy tasks crossing an implicit
  artifact-readiness boundary require schema-4 amendment.

## Dispatch one block

Process one block and stop unless the user explicitly requested uninterrupted
execution. A bracketed block contains at most 2 independent tasks and must run
concurrently; confirm disjoint writes and no sibling-produced input first.

Require preceding tasks to be `DONE` and every required materialization and
handoff to report a concrete ready state. Set current tasks to `IN_PROGRESS` by
changing only their status lines.

Route workers under `rules/subagents.md`: `builder` for bounded implementation
and semantic judgement, and `explorer` for read-only work. Use
`artifact-writer` for a Haiku task that writes approved documentation, static
fixture data, or the plan bundle. Pass the explicit model,
model reason, full task contract, relevant baseline, decisions, test-matrix
rows, dependencies, and earlier handoffs. Agent definitions and global rules
are the worker contract; do not restate them in every prompt.

An incomplete worker is a failed dispatch. Checkpoint its evidence and stop;
do not continue, replace, or repair it in the parent.

## Record outcomes

- Compare all changed paths, including materialization side effects, with
  `Writes`. Undeclared paths require plan amendment.
- Require every declared skill in the worker receipt.
- For `CI`, mark `DONE` when the artifact and handoff are ready and record the
  check as pending CI.
- For `Local`, mark `DONE` only after the declared targeted check passes. Record
  `FAILED` and stop on failure.
- For `Manual`, retain `IN_PROGRESS`, record the ready state and exact user
  action, then stop. Apply the user's reported outcome on the next invocation.
- Record worker errors as `FAILED`. Preserve successful siblings in a parallel
  block before stopping.

Write only the result fields defined in the task template; never include raw
logs. Any new decision, dependency, credential need, expanded write scope, or
uncertain external state requires plan amendment.

## Finish

Refresh statuses once after checkpointing. When all tasks are `DONE`, reply
`Done`. When uninterrupted execution was requested, continue with the next
block; otherwise reply `Checkpointed <block>; run plan-execute again for the
next block.` On failure, reply `Blocked on <task ID>: <exact problem>`.
