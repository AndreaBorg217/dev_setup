---
name: planner
description: Use when the user asks to plan, scope, or break down multi-step work before implementation, or says "plan this" / "write a plan" - covers plan-directory creation, feature-spec gating, forecast-blocker classification, and task-graph composition consumed by plan-execute.
---

# Planner

Runs on Opus. Investigates via Haiku/Sonnet subagents, then writes a self-contained plan directory that a fresh Sonnet orchestrator (via `plan-execute`) can pick up after `/clear` with zero prior context.

## Step 0 - Mode check

Plan mode is the expected mode for this skill - it is how `opusplan` routes to Opus. Detect it by the presence of a harness-assigned plan file path in the system prompt.

- **In plan mode**: the harness plan file is a *staging buffer*, not the deliverable. Compose the global sections and task graph into it (Step 9), present and call `ExitPlanMode` (Step 9). Because plan mode is read-only, you cannot materialize the final files yourself. Instead, upon calling `ExitPlanMode`, you must explicitly instruct Sonnet to materialize `CONTEXT.md`/`PLAN.md`/`PLAN.HUMAN.md` to disk immediately, and then **stop completely** so the user can `/clear` the context. **Named exception:** `$plandir` itself and `FEATURE_SPEC.md` are written to disk in Step 1/Step 2, before approval, regardless of plan mode - `feature-spec` has no plan-mode awareness and writes as soon as its spec is accepted. Plan mode's staging-buffer guarantee covers `CONTEXT.md`/`PLAN.md`/`PLAN.HUMAN.md` only, not the plan directory's existence or the feature spec.
- **Not in plan mode**: skip the staging buffer - write plan-directory artifacts to disk directly as each lifecycle step completes, and warn the user once that the session model may not be Opus.
- **Never dispatch `opus` subagents.** `CLAUDE_CODE_SUBAGENT_MODEL` is `inherit`, and this skill's session is Opus - an `Agent` call with no explicit `model` silently inherits Opus. Every dispatch from this skill MUST pass `model: "sonnet"` or `model: "haiku"` explicitly. Opus is a rare, user-invoked escape valve for architectural blocker amendment (see Step 7's "No generic review tasks" bullet) - the planner never reaches for it on its own.

## Lifecycle

This skill follows a fixed 11-step lifecycle. Steps 1-11 below correspond 1:1 to it.

## Step 1 - Select or create the plan directory

Plans live at `plans/<kebab-case-name>/` under the repo root, containing up to `FEATURE_SPEC.md`, `CONTEXT.md`, `PLAN.md`, `PLAN.HUMAN.md`. Exactly one `PLAN.md` per plan, amended in place - never forked, versioned, or `.bak`'d.

1. `root=$(git rev-parse --show-toplevel)`. If cwd is not a git repo, halt (see Halt conditions) and ask.
2. Derive a kebab-case slug from the ask, or use the plan name the user gave.
3. Check `$root/plans/<slug>/`. If it already exists, this is a **resume/amend of that plan**, not a new one - load its existing artifacts and continue the lifecycle against them. Never create a second directory or a versioned copy for the same piece of work. If it does not exist, `mkdir -p` it now - the directory must exist on disk before Step 2 can invoke `feature-spec`, which writes into it directly, regardless of plan mode.
4. If the ask is genuinely ambiguous about whether it targets an existing plan directory or a new one, halt via `AskUserQuestion` and ask which.

## Step 2 - Load the feature spec

If the ask is a brand-new feature (not a refactor, investigation, or bug fix), invoke the `feature-spec` skill first, passing it the `$plandir` (the exact `plans/<slug>/` path resolved in Step 1). Do not proceed to Step 3 until that spec is accepted - a plan built on an unclear feature ask will be wrong at every downstream task.

The accepted spec lands at `$plandir/FEATURE_SPEC.md` because `$plandir` was supplied, so `feature-spec` never derives its own, possibly-different slug for this call. Record the revision/hash `feature-spec` reports back - this gets written into `PLAN.md` at Step 9, and is what lets a later re-run detect that the spec changed underneath a plan and amend affected pending tasks before execution.

## Step 3 - Ask, then investigate

Run one `AskUserQuestion` round first (batch these, they don't depend on each other):

1. **Scope boundary** - what is explicitly in and out of scope for this plan.
2. **Deployment in scope?** - yes/no.
3. **If yes: runbook skeleton** - request the user's draft commands, target environments, and any verification hooks they already know about. Deployment planning does not proceed without this input - do not invent a deployment runbook from scratch.

Then dispatch investigation subagents in parallel, one message, multiple tool calls, per `rules/subagents.md` tiering:

- **Haiku** - locate/grep code, read logs, fetch docs or web pages, doc retrieval, mechanical/build/lint/compile/import/poll checks, noisy-output compaction, artifact consistency checks. Prefer `cavecrew-investigator` for pure code-location work; otherwise `Explore` with `model: "haiku"` instead (plan mode restricts Phase-1-style investigation to `Explore`). Default choice for exploration.
- **Sonnet** - substantive implementation reads, non-mechanical debugging, integrating repo patterns, ambiguous or design-bearing code, anything where judgment is needed to summarize correctly.

Never call `WebSearch`/`WebFetch` from the main thread - delegate to a Haiku subagent and have it return only the sourced finding, not raw page content. Each subagent returns a conclusion, file/line evidence, a caveat, and a proposed finding ID only - not raw command output. Batch related lookups into one dispatch rather than firing many tiny subagents; don't dispatch at all when call overhead exceeds the work. If a subagent errors or comes back empty on a fact the plan depends on, see Halt conditions - do not proceed on a guess.

## Step 4 - Write findings to CONTEXT.md

`CONTEXT.md` is a compact evidence cache, not a transcript. Only findings that are expensive to rediscover, reusable, evidenced, and time/condition-bound belong in it. Use the `F<N>` finding skeleton in `plan-template.md`'s `## CONTEXT.md` section.

Organize under sections: stable / volatile / execution discoveries / invalidated. Never store raw logs, full files, conversation history, duplicated requirements, secrets, or volatile state framed as durable. Volatile or destructive preconditions are always rechecked at execution time, never trusted as still-true. Tasks reference finding IDs only, never the whole file. Soft limit 12-16 KB.

**Lightweight-plan exception**: for a lightweight plan (single block, at most 3 tasks, no deployment, no architectural blockers), create `CONTEXT.md` only if investigation actually produced a cacheable finding - otherwise skip it.

## Step 5 - Identify and classify forecast blockers

A forecast blocker is a plausible reason a task in the eventual graph might not work as planned. Capture each using the `B<N>` blocker skeleton in `plan-template.md`'s `## PLAN.md` -> Forecast blockers section, with one addition at planning time only: the persisted template's `Materiality` field offers `non-material | task-local`; while classifying here, add a third option, `architectural`, for blockers resolved before `PLAN.md` is written (see Step 6) - it never appears in the persisted file since architectural blockers are gone by the time `PLAN.md` exists.

Classify every blocker by materiality **before** composing the task graph in Step 7.

## Step 6 - Probe architectural-tier blockers now

Probe every **architectural**-tier blocker immediately, in this same pass, using Haiku or Sonnet - never Opus for the probe. If a probe result is unresolved or invalidates the plan's premise, halt (see Halt conditions) before writing anything further and ask the user - do not compose a task graph around an unverified architectural assumption. If resolved, write the finding into `CONTEXT.md` (Step 4's format) and proceed.

Non-material and task-local blockers are not probed here - they are carried forward, unresolved, into `PLAN.md`'s Forecast blockers section for `plan-execute` to handle at execution time (non-material: record and continue; task-local: amend the task contract in place if architecture/dependencies are unchanged). If one of those turns out to be architectural after all once `plan-execute` gets to it, that is a halt condition there too, not something this skill can fix in advance.

## Step 7 - Create the task graph

- **Task IDs** - `t<N>-<kebab-slug>`, stable once assigned, referenced by other tasks' Dependencies field.
- **Caveman-shaped tasks** - scope each task, wherever the work allows, to fit one of `rules/subagents.md`'s caveman shapes so `plan-execute` can dispatch `cavecrew-builder`/`cavecrew-reviewer`/`cavecrew-investigator` instead of `general-purpose`: a build/edit task bounded to 1-2 files, a review/verification task scoped to one diff or file, a locate task scoped to a grep/find question. If a task's How genuinely needs 3+ files touched in one dispatch or spans concerns no single caveman shape covers, split it into smaller tasks rather than leaving one broad task for `general-purpose`.
- **No generic review tasks** - do not add a same-model "reread the implementation and check it" task with no specific fault hypothesis. Only include a review-shaped task when it is one of: deterministic verification (an assertion with an observable pass/fail), targeted investigation of a suspected fault, external/human review, or an explicitly requested specialist review. Opus plan review is never auto-inserted here - it is a user-initiated escape valve, invoked only when an execution-time blocker materially invalidates the approved plan.
- **Required per-task contract**:

```
### t1-task-name
Status: / Model: / Goal: / Why: / How: / Context: / Verification: / Dependencies: / Results:
```

  - **Status**: `PENDING` | `IN_PROGRESS` | `BLOCKED` | `DONE` | `FAILED`.
  - **Model**: `haiku` | `sonnet`, per the Model routing rules above - haiku for mechanical/search/build/test/poll/doc-sync work, sonnet for implementation, non-mechanical debugging, or anything ambiguous. If a task will itself need further delegation at execution time, the planner does not enumerate those sub-dispatches - `plan-execute` picks their models.
  - **Why**: one line linking the task back to the objective or an accepted decision - not restated scope.
  - **Context**: the `CONTEXT.md` finding IDs (e.g. `F1, F3`) this task's executor should read - never the whole file, never a copy of the finding text.
  - **Verification**: an observable artifact assertion - an exit code, a file that must exist, a query result, a table filled into Results. Never "looks correct" or other unfalsifiable language.
  - **Results**: left blank at plan time; filled in by whoever executes the task.
- **Parallelism line and blocks** - one line at the top of the Tasks section encoding the DAG, e.g. `Parallelism: t1 >> [t2, t3] >> t4`. Each `>>`-separated segment is one **block** - a block is one or more tasks that `plan-execute` dispatches together in a single invocation before checkpointing and stopping. `t1 >> [t2, t3] >> t4` is 3 blocks: block 1 is `t1`, block 2 is `[t2, t3]`, block 3 is `t4`. The Parallelism line must stay consistent with every task's Dependencies field. A group may only contain tasks classified Independent per `rules/subagents.md` -> Parallelism judgement. If 2 tasks cannot run in 2 parallel subagents at the same time they must be `t1 >> t2` not `[t1, t2]`.
- **Deployment tasks** - stg and prod are ALWAYS separate tasks, never combined:
  - The **stg task** expands the user's runbook skeleton into concrete commands, with a verification step after each command. On verification failure, amend the failing step and re-verify - repeat until the stg task's Status is `DONE` with a passed verification recorded in Results.
  - The **prod task** depends on the stg task's ID and restates the *amended* runbook (the version that actually passed on stg, not the original skeleton). It must not be dispatched until the stg task is `DONE`.
- **Manual actions** - list every check only the human user can perform: approvals, dashboard eyeballing, anything with a side effect the agent must not trigger unilaterally. Per `rules/safety.md`, conclusive operations (commits, pushes, MRs, Slack messages, Jira tickets, anything that could email someone) are never auto-run by the plan and must appear here or be marked as requiring explicit approval in the task's How field.
- **Shared-dependency fanout pattern** - apply the probe-then-fanout order from `rules/subagents.md` -> Parallelism judgement: `t_change` (shared unit) `>>` `t_probe` (its own group, single consumer) `>>` `[t_fanout_2 .. t_fanout_N]` (remaining consumers, each `Dependencies: t_probe`, only dispatched once `t_probe` is `DONE`). `t_probe`'s Verification must require the concrete adaptation - exact diff/commands/config - to be written into its Results, not just pass/fail. Each fanout task's How must say to reuse that recorded adaptation verbatim.
- **Self-containment gate** - before writing the file, confirm: could a fresh Sonnet orchestrator with zero prior context execute this plan end to end? All paths must be absolute, all repo/service names spelled out, all commands and acceptance criteria written inline. No task may reference "this conversation," "as discussed," or "the earlier exploration."

## Step 8 - Verify feature-spec completeness against the graph

Walk every accepted requirement in `$plandir/FEATURE_SPEC.md` and confirm at least one task in the Step 7 graph covers it. If a requirement has no owning task, that is a gap in the graph, not an acceptable omission - go back to Step 7. If the gap instead reveals the spec itself is unclear or incomplete, halt (see Halt conditions).

## Step 9 - Write PLAN.md

Compose the full `PLAN.md` body using the skeleton in `plan-template.md`, which is the source of truth for exact section content and ordering. `PLAN.md` contains, in order: `Execution Contract / Objective / Invariants / Non-goals / Allowed files / Forbidden changes / Accepted decisions / Rejected decisions / Validation policy / Deployment boundary / Forecast blockers / Execution checkpoint / Tasks / Deployment / Manual actions`. These constraints (Invariants, Forbidden changes, Deployment boundary, etc.) go into every affected task dispatch at execution time, not just stated once at the top. Record the feature-spec revision/hash from Step 2, and carry forward every unresolved non-material or task-local blocker from Step 5 into the Forecast blockers section for `plan-execute` to consume.

- **In plan mode**: compose this body into the harness plan file (the staging buffer from Step 0). Show the plan summary (headline + task list + parallelism groups) to the user, then call `ExitPlanMode`. Do not attempt to write the files to disk yourself, as plan mode is read-only. Instead, clearly output strict instructions for Sonnet to execute the materialization steps immediately below and then stop.
- **Post-approval materialization (delegated to Sonnet in plan mode; runs immediately by you in non-plan mode)**:
  1. `$root/plans/<slug>/` and `FEATURE_SPEC.md` already exist from Step 1/Step 2 - nothing to create here.
  2. Write `CONTEXT.md` (if produced) and `PLAN.md` into `$plandir`. If `$plandir/PLAN.md` already existed (Step 1 resume case), amend it in place - do not write a second copy, a `.v2`, or a `.bak`.
  3. Verify: `PLAN.md` exists, is non-empty, and contains both a `## Tasks` line and a `Parallelism:` line. Report the absolute path to the user.
  4. **HALT**: Once files are verified, state that the context must be cleared and halt execution entirely so the user can run `/clear`. Do not proceed to implementation.

## Step 10 - Generate PLAN.HUMAN.md

Regenerate only after a material graph/meaning change - not for cosmetic edits. For a lightweight plan (Step 4's exception), write it inline yourself, no dispatch. Otherwise dispatch a Haiku subagent to generate it from the objective, task IDs/names, short `Why`, goals, dependencies, parallelism, and manual actions only - no repo inspection, no redesign. Use the skeleton in `plan-template.md`. `PLAN.HUMAN.md` is not authoritative; its checkboxes are updated mechanically as `PLAN.md` changes.

## Step 11 - Stop

This skill never executes implementation tasks - that is `plan-execute`'s job, invoked separately against the `PLAN.md` this skill produced.

## Halt conditions

On any of the following, stop immediately, do not compose or write plan-directory artifacts further, and ask the user via `AskUserQuestion` for the clarification needed to unblock. Do not guess, do not retry the same operation, do not narrow scope unilaterally:

- `feature-spec` was required (Step 2) but not accepted.
- Scope answers from Step 3 are mutually contradictory or too vague to bound tasks.
- A repo, service, or path named in the ask cannot be located.
- A Step 3 investigation subagent returns an error or an empty/unusable finding on a fact the plan depends on.
- Deployment is in scope but the user supplied no runbook skeleton (Step 3, question 3).
- An architectural-tier forecast blocker (Step 6) comes back unresolved or invalidates the plan's premise.
- The Step 7 self-containment gate cannot be satisfied because a required fact is unknown.
- Step 8 finds a feature-spec requirement with no owning task, and the fix isn't a straightforward graph addition.
- cwd is not a git repo, so the plan directory path (Step 1) cannot be resolved.
- The ask is ambiguous about whether it targets an existing plan directory or a new one (Step 1).
- The post-approval materialization write (Step 9) was blocked, or its verification failed.

State what is blocked, what is needed, and stop - do not present a partial plan as if complete.

## Related files

- `plan-template.md` - the literal skeleton this skill fills in when composing `PLAN.md` and `PLAN.HUMAN.md`.
- `FEATURE_SPEC.md`, `CONTEXT.md`, `PLAN.HUMAN.md` are not sibling skill files - they are per-plan artifacts this skill produces at `plans/<slug>/`, alongside `PLAN.md`.
- For what a "block" is, see Step 7 - this skill only defines block boundaries; it never dispatches a block itself.
