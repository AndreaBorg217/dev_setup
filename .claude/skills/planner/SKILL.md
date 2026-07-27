---
name: planner
description: Use when the user asks to plan, scope, or break down multi-step work before implementation, or says "plan this" / "write a plan" - produces PLAN.md at repo root for later execution by the plan-execute skill.
---

# Planner

Runs on Opus. Investigates via Haiku/Sonnet subagents, then writes a self-contained `PLAN.md` at the repo root that a fresh Sonnet orchestrator (via `plan-execute`) can pick up after `/clear` with zero prior context.

## Step 1 - Preconditions

This skill only produces `PLAN.md`. It never edits application code directly.

If the ask is a brand-new feature (not a refactor, investigation, or bug fix), invoke the `feature-spec` skill first. Do not proceed to Step 2 until that spec is accepted - a plan built on an unclear feature ask will be wrong at every downstream task.

## Step 2 - Ask

Run one `AskUserQuestion` round (batch these three, they don't depend on each other):

1. **Scope boundary** - what is explicitly in and out of scope for this plan.
2. **Deployment in scope?** - yes/no.
3. **If yes: runbook skeleton** - request the user's draft commands, target environments, and any verification hooks they already know about. Deployment planning does not proceed without this input - do not invent a deployment runbook from scratch.

## Step 3 - Gather

Dispatch investigation subagents in parallel, one message, multiple tool calls. Follow `rules/subagents.md` tiering:

- **Haiku** - locate/grep code, read logs, fetch docs or web pages, run mechanical checks. Prefer `cavecrew-investigator` agent type for pure code-location work.
- **Sonnet** - ambiguous reads, design-bearing code, anything where judgment is needed to summarize correctly.

Never call `WebSearch`/`WebFetch` from the main thread - delegate to a Haiku subagent and have it return only the sourced finding, not raw page content.

Each subagent returns findings only (file:line references, summarized conclusions) - not raw command output. Batch related lookups into one dispatch rather than firing many tiny subagents.

## Step 4 - Compose PLAN.md

Write `PLAN.md` at the repo root using the skeleton in `plan-template.md`. Enforce these rules:

- **Task IDs** - `t<N>-<kebab-slug>`, stable once assigned, referenced by other tasks' Dependencies field.
- **Required fields per task** - ID, Status, Model, Goal, How, Verification, Dependencies, Results.
  - **Status**: `PENDING` | `IN_PROGRESS` | `BLOCKED` | `DONE` | `FAILED`.
  - **Model**: `haiku` | `sonnet`, chosen per `rules/subagents.md` - haiku for mechanical/search/build/test/poll work, sonnet for implementation, review, or anything ambiguous.
  - **Verification**: an observable artifact assertion - an exit code, a file that must exist, a query result, a table filled into Results. Never "looks correct" or other unfalsifiable language.
  - **Results**: left blank at plan time; filled in by whoever executes the task.
- **Parallelism line** - one line at the top of the Tasks section encoding the DAG, e.g. `Parallelism: t1 >> [t2, t3] >> t4`. This must stay consistent with every task's Dependencies field - if t3 depends on t1, t3 cannot appear before t1 in the chain.
- **Deployment tasks** - stg and prod are ALWAYS separate tasks, never combined:
  - The **stg task** expands the user's runbook skeleton into concrete commands, with a verification step after each command. On verification failure, amend the failing step and re-verify - repeat until the stg task's Status is `DONE` with a passed verification recorded in Results.
  - The **prod task** depends on the stg task's ID and restates the *amended* runbook (the version that actually passed on stg, not the original skeleton). It must not be dispatched until the stg task is `DONE`.
- **Manual section** - list every check only the human user can perform: approvals, dashboard eyeballing, anything with a side effect the agent must not trigger unilaterally. Per `rules/safety.md`, conclusive operations (commits, pushes, MRs, Slack messages, Jira tickets, anything that could email someone) are never auto-run by the plan and must appear here or be marked as requiring explicit approval in the task's How field.
- **Self-containment gate** - before writing the file, confirm: could a fresh Sonnet orchestrator with zero prior context execute this plan end to end? All paths must be absolute, all repo/service names spelled out, all commands and acceptance criteria written inline. No task may reference "this conversation," "as discussed," or "the earlier exploration."

## Step 5 - Council review (mandatory)

Before presenting, invoke the `council` skill on the composed `PLAN.md` draft - every plan, not only ones flagged as risky. Ask the 5 Advisors to stress-test task ordering, missed dependencies, weak verification gates, and deployment safety. Council's own internal subagent dispatch stays on `sonnet`/`haiku` per `rules/subagents.md` tiering - invoking council does not escalate any task's Model field to opus. Fold any objection into the task list (new task or dependency) or into the Manual section (a check the user must perform). Re-run the self-containment gate from Step 4 if the plan changed.

## Step 6 - Present

Show the plan summary (headline + task list + parallelism groups) to the user and stop. Do not begin execution from this skill - that is `plan-execute`'s job.

## Related files

- `plan-template.md` - the literal PLAN.md skeleton this skill fills in.
