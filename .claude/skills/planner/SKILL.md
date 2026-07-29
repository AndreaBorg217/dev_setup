---
name: planner
description: Use when the user asks to plan, scope, or break down multi-step work before implementation, or says "plan this" / "write a plan" - produces PLAN.md at repo root for later execution by the plan-execute skill.
---

# Planner

Runs on Opus. Investigates via Haiku/Sonnet subagents, then writes a self-contained `PLAN.md` at the repo root that a fresh Sonnet orchestrator (via `plan-execute`) can pick up after `/clear` with zero prior context.

## Step 0 - Mode check

Plan mode is the expected mode for this skill - it is how `opusplan` routes to Opus. Detect it by the presence of a harness-assigned plan file path in the system prompt.

- **In plan mode**: the harness plan file is a *staging buffer*, not the deliverable. Compose `PLAN.md`'s body into it (Step 4), present and call `ExitPlanMode` (Step 5), then materialize the real `PLAN.md` at the repo root only after approval (Step 6). The skill is not done until Step 6 passes.
- **Not in plan mode**: skip the staging buffer - write repo-root `PLAN.md` directly in Step 4, and warn the user once that the session model may not be Opus.
- **Never dispatch `opus` subagents.** `CLAUDE_CODE_SUBAGENT_MODEL` is `inherit`, and this skill's session is Opus - an `Agent` call with no explicit `model` silently inherits Opus. Every dispatch from this skill MUST pass `model: "sonnet"` or `model: "haiku"` explicitly.

## Step 1 - Preconditions

This skill only produces `PLAN.md`. It never edits application code directly.

If the ask is a brand-new feature (not a refactor, investigation, or bug fix), invoke the `feature-spec` skill first. Do not proceed to Step 2 until that spec is accepted - a plan built on an unclear feature ask will be wrong at every downstream task.

## Halt conditions

On any of the following, stop immediately, do not compose or write `PLAN.md`, and ask the user via `AskUserQuestion` for the clarification needed to unblock. Do not guess, do not retry the same operation, do not narrow scope unilaterally:

- `feature-spec` was required (per Step 1) but not accepted.
- Scope answers from Step 2 are mutually contradictory or too vague to bound tasks.
- A repo, service, or path named in the ask cannot be located.
- A Step 3 investigation subagent returns an error or an empty/unusable finding on a fact the plan depends on.
- Deployment is in scope but the user supplied no runbook skeleton (see Step 2, question 3).
- The Step 4 self-containment gate cannot be satisfied because a required fact is unknown.
- cwd is not a git repo, so `$root/PLAN.md` (Step 6) cannot be resolved.
- `$root/PLAN.md` already exists and the user has not chosen how to handle it (Step 6).
- The post-approval write to `$root/PLAN.md` was blocked, or Step 6's verification failed.

State what is blocked, what is needed, and stop - do not present a partial plan as if complete.

## Step 2 - Ask

Run one `AskUserQuestion` round (batch these three, they don't depend on each other):

1. **Scope boundary** - what is explicitly in and out of scope for this plan.
2. **Deployment in scope?** - yes/no.
3. **If yes: runbook skeleton** - request the user's draft commands, target environments, and any verification hooks they already know about. Deployment planning does not proceed without this input - do not invent a deployment runbook from scratch.

## Step 3 - Gather

Dispatch investigation subagents in parallel, one message, multiple tool calls. Follow `rules/subagents.md` tiering:

- **Haiku** - locate/grep code, read logs, fetch docs or web pages, run mechanical checks. Prefer `cavecrew-investigator` agent type for pure code-location work. Default choice for exploration - use Haiku unless the read genuinely needs judgment.
- **Sonnet** - ambiguous reads, design-bearing code, anything where judgment is needed to summarize correctly.

In plan mode, Phase 1-style investigation is restricted to the `Explore` subagent type. Satisfy both rules at once: use `Explore` with `model: "haiku"` for location/grep work. Reserve `cavecrew-investigator` for non-plan-mode invocations of this skill.

Hard constraint: every subagent this skill dispatches from this Opus thread, for any purpose, must be `sonnet` or `haiku` - never `opus`. When the work is pure exploration/location, prefer `haiku` over `sonnet`.

Never call `WebSearch`/`WebFetch` from the main thread - delegate to a Haiku subagent and have it return only the sourced finding, not raw page content.

Each subagent returns findings only (file:line references, summarized conclusions) - not raw command output. Batch related lookups into one dispatch rather than firing many tiny subagents.

If a subagent errors or comes back empty on a fact the plan depends on, see Halt conditions above - do not proceed on a guess.

## Step 4 - Compose (into the staging buffer)

Compose the full `PLAN.md` body using the skeleton in `plan-template.md`. In plan mode, write this body into the harness plan file (the staging buffer from Step 0) - not the repo root yet, that happens in Step 6. Out of plan mode, write it straight to repo-root `PLAN.md`. Enforce these rules:

- **Task IDs** - `t<N>-<kebab-slug>`, stable once assigned, referenced by other tasks' Dependencies field.
- **Caveman-shaped tasks** - scope each task, wherever the work allows, to fit one of `rules/subagents.md`'s caveman shapes so `plan-execute` can dispatch `cavecrew-builder`/`cavecrew-reviewer`/`cavecrew-investigator` instead of `general-purpose`: a build/edit task bounded to 1-2 files, a review/verification task scoped to one diff or file, a locate task scoped to a grep/find question. If a task's How genuinely needs 3+ files touched in one dispatch or spans concerns no single caveman shape covers, split it into smaller tasks along those lines rather than leaving one broad task for `general-purpose`.
- **Required fields per task** - ID, Status, Model, Goal, How, Verification, Dependencies, Results.
  - **Status**: `PENDING` | `IN_PROGRESS` | `BLOCKED` | `DONE` | `FAILED`.
  - **Model**: `haiku` | `sonnet`, chosen per `rules/subagents.md` - haiku for mechanical/search/build/test/poll work, sonnet for implementation, review, or anything ambiguous.
  - **Verification**: an observable artifact assertion - an exit code, a file that must exist, a query result, a table filled into Results. Never "looks correct" or other unfalsifiable language.
  - **Results**: left blank at plan time; filled in by whoever executes the task.
  - **Model** is the model of the subagent that will execute this task, chosen by the planner per `rules/subagents.md`. If a task will itself need further delegation at execution time, the planner does not enumerate those sub-dispatches - the orchestrator picks their models (see `plan-execute` SKILL.md Step 3, Model discipline).
- **Parallelism line** - one line at the top of the Tasks section encoding the DAG, e.g. `Parallelism: t1 >> [t2, t3] >> t4`. This must stay consistent with every task's Dependencies field - if t3 depends on t1, t3 cannot appear before t1 in the chain. A group may only contain tasks classified Independent per `rules/subagents.md` -> Parallelism judgement; apply that classification before grouping.
- **Deployment tasks** - stg and prod are ALWAYS separate tasks, never combined:
  - The **stg task** expands the user's runbook skeleton into concrete commands, with a verification step after each command. On verification failure, amend the failing step and re-verify - repeat until the stg task's Status is `DONE` with a passed verification recorded in Results.
  - The **prod task** depends on the stg task's ID and restates the *amended* runbook (the version that actually passed on stg, not the original skeleton). It must not be dispatched until the stg task is `DONE`.
- **Manual section** - list every check only the human user can perform: approvals, dashboard eyeballing, anything with a side effect the agent must not trigger unilaterally. Per `rules/safety.md`, conclusive operations (commits, pushes, MRs, Slack messages, Jira tickets, anything that could email someone) are never auto-run by the plan and must appear here or be marked as requiring explicit approval in the task's How field.
- **Shared-dependency fanout pattern** - apply the probe-then-fanout order from `rules/subagents.md` -> Parallelism judgement: `t_change` (shared unit) `>>` `t_probe` (its own group, single consumer) `>>` `[t_fanout_2 .. t_fanout_N]` (remaining consumers, each `Dependencies: t_probe`, only dispatched once `t_probe` is `DONE`). `t_probe`'s Verification must require the concrete adaptation - exact diff/commands/config - to be written into its Results, not just pass/fail. Each fanout task's How must say to reuse that recorded adaptation verbatim.
- **Self-containment gate** - before writing the file, confirm: could a fresh Sonnet orchestrator with zero prior context execute this plan end to end? All paths must be absolute, all repo/service names spelled out, all commands and acceptance criteria written inline. No task may reference "this conversation," "as discussed," or "the earlier exploration."

## Step 5 - Present + exit

Show the plan summary (headline + task list + parallelism groups) to the user. In plan mode, call `ExitPlanMode` next - do not present the plan as done yet, `PLAN.md` does not exist at the repo root at this point. Out of plan mode, this step just stops; Step 6 does not apply.

## Step 6 - Materialize (post-approval, mandatory in plan mode)

Runs only after `ExitPlanMode` is approved. This step is what makes the skill done - a presented-but-unmaterialized plan is not complete.

1. `root=$(git rev-parse --show-toplevel)`. If cwd is not a git repo, halt (see Halt conditions) and ask.
2. If `$root/PLAN.md` already exists, halt via `AskUserQuestion` with options: overwrite / archive to `PLAN.md.bak` then write / abort. Never clobber silently - an existing `PLAN.md` may be mid-execution with populated Status/Results.
3. Run `cp <harness-plan-file-path> "$root/PLAN.md"`. Do not `Read` the harness plan file into context and `Write` it back out - `cp` moves identical bytes for zero tokens.
4. Verify: `$root/PLAN.md` exists, is non-empty, and contains both a `## Tasks` line and a `Parallelism:` line. Report the absolute path to the user.
5. If the write is refused, blocked, or verification fails, halt (see Halt conditions) and report - do not claim the plan is complete.

Do not begin execution from this skill - that is `plan-execute`'s job.

## Related files

- `plan-template.md` - the literal PLAN.md skeleton this skill fills in.
