---
name: planner
description: Use when the user asks to plan, scope, or break down multi-step work before implementation, or says "plan this" / "write a plan" - resolves technical blockers during planning and produces self-contained PLAN.md consumed by plan-execute.
---

# Planner

Run on Opus. Produce one `plans/<kebab-name>/PLAN.md` that a fresh Sonnet `plan-execute` session can execute without this conversation. Follow `rules/subagents.md` for any delegated investigation.

## 1. Mode and intent

Detect plan mode from the harness-assigned plan-file path in the system prompt.

- **Plan mode:** use the harness file as the staging copy. Keep planning until it is complete and call `ExitPlanMode`; do not ask for a separate signoff first. After approval, materialize that exact approved content at the repository plan path, reply `Done`, and stop before implementation.
- **Other modes:** perform the same investigation and validation, present the completed plan once for explicit approval, then materialize it, reply `Done`, and stop. Warn once that the session may not be Opus.
- Never dispatch Opus from this skill. Route Haiku/Sonnet work under `rules/subagents.md` and pass the model explicitly.

Treat user intent and technical facts differently:

- Obtain behavior, scope, tradeoffs, and acceptance criteria from explicit user statements or approval.
- Establish technical facts from inspected code, configuration, commands, tests, or authoritative documentation.
- If evidence conflicts with stated intent or exposes multiple behavior choices, present it and ask the user. Never silently choose.

Unless explicitly requested, exclude git operations, deployment, test-file changes, and documentation changes. Relevant existing tests, lint, builds, and artifact checks may be run for verification.

Scale depth to blast radius. A small change with one obvious implementation still gets a complete plan when this skill was explicitly invoked, but it needs only the evidence and tasks required to make that plan executable. Apply fuller scrutiny to new modules, schemas, authentication, money, migrations, deletion, external state, and other high-risk work.

## 2. Select the plan

1. Resolve the repository root with `git rev-parse --show-toplevel`; halt outside a git repository.
2. Use a user-supplied plan name or mechanically slug an unambiguous objective as kebab-case.
3. Target `$root/plans/<slug>/PLAN.md` without creating it yet.
4. Treat an existing plan as an amendment only when the request identifies it or the user confirms the match. Amend it in place; never fork, version, or create a backup copy.

## 3. Investigate and resolve blockers

Apply the investigate-before-asking rules in `rules/workflow.md`. Raise inconsistent evidence instead of choosing an interpretation silently.

After that investigation, ask at most three unresolved user-owned questions at a time, give each a recommended default, and wait. Include only candidate assumptions relevant to those decisions. Make each assumption specific and falsifiable; consider data, failure behavior, API boundaries, state, environment, scope, and testing only when the task touches them.

Resolve technical assumptions through evidence. Convert accepted user-owned assumptions into explicit boundaries or decisions, and never carry an unsupported assumption into the completed plan. If no blocking question remains, continue directly instead of emitting an empty questionnaire.

Use the main thread for small reads and bounded commands. Delegate noisy, broad, or parallel investigation under `rules/subagents.md`.

A forecast blocker is a credible, evidenced reason the intended approach could fail or force a plan change. Resolve every forecast blocker now:

1. Dispatch bounded Haiku/Sonnet probes, parallelizing independent probes.
2. Incorporate conclusive technical outcomes into the plan's Grounded facts or task instructions.
3. Ask the user when an outcome changes behavior, architecture, dependencies, scope, or another user-owned choice.
4. Halt if a required probe remains inconclusive or unavailable.

Never carry an unresolved forecast blocker into execution. A runtime availability check may remain only as a deterministic task precondition whose failure response is already fixed and cannot change the approved approach.

## 4. Compose the execution blocks

Read `plan-template.md` before composing. Use its section order and task fields exactly.

- **Objective:** restate the requested outcome in complete terms and include the acceptance criteria used to judge completion.
- **Boundaries and decisions:** record each material assumption as a specific, falsifiable, user-approved constraint. For a meaningful design choice, name the selected option and reject the principal alternative in one clause with the reason.
- **Grounded facts:** cite the exact repository or authoritative evidence for every technical fact the executor must rely on.
- **IDs:** assign stable full IDs in the form `t<N>-<kebab-title>`. Use the full ID everywhere; no shorthand aliases.
- **Titles:** make each title concise and specific enough for a developer to understand by skimming the task headings.
- **Tasks:** define coherent, independently verifiable outcomes rather than forcing a file-count limit. Include exact paths, commands, and important function/type/interface signatures in `How`.
- **Writes:** list comma-separated paths/globs the task may modify, or `None` for read-only work.
- **Models:** assign the task model under `rules/subagents.md`; only `haiku` and `sonnet` are valid in a plan.
- **Verification:** require an observable assertion such as an exit code, file state, query result, or table; never "looks correct."
- **Blocks:** encode order once as `Blocks: <full-id> >> [<full-id>, <full-id>]`. Each `>>`-separated segment is exactly one `plan-execute` invocation followed by a stop. `t1 >> [t2, t3, t4] >> t5` means: run `t1` alone and stop; on the next invocation, dispatch `t2`, `t3`, and `t4` concurrently in three separate subagents and stop; on the next invocation, run `t5` alone and stop.
- **Brackets:** use brackets only for tasks that are mutually independent, share no required intermediate output, and can run concurrently in separate subagents without overlapping Writes. Never bracket tasks that must run sequentially. Do not add per-task Dependencies.
- **Fanout:** apply the probe-then-fanout pattern in `rules/subagents.md` and reference the probe's full task ID in consumer `How` fields.
- **External effects:** include git operations, deployment, test-file changes, or documentation changes only when explicitly requested and record that inclusion under Boundaries and decisions.
- **Deployment:** when explicitly requested, keep staging and production in separate sequential blocks; production uses and depends on the verified staging outcome.
- **Manual actions:** add the optional section only for actions the user must perform.
- **Final code-conformance pass:** when any task creates or modifies source code,
  scripts, migrations, tests, infrastructure-as-code, or other executable logic,
  add one final unbracketed `sonnet` task after every code-writing task. Its `How`
  must require dispatch to one `general-purpose` review subagent and invocation
  of `.claude/skills/review-code/SKILL.md` in repair mode over the complete
  planned code change. The `How` must name every preceding code-writing task by
  full ID and use their Results to distinguish planned changes from unrelated
  dirty-worktree changes. It must require conformity with
  `.claude/rules/coding.md` and then run the configured linter, formatter check,
  type checker, and full test suite.
  Give it `Writes` equal to the exact union of code paths/globs already
  authorized for earlier tasks so it can remove findings without broadening
  scope. Its `Verification` must rerun every configured check and invoke the
  review skill in verification mode in a fresh `sonnet` `general-purpose`
  subagent; all checks and that independent review must pass. Do not add a
  separate final verification task, and do not permit any later task to modify
  code; explicitly requested git or deployment work may follow only after this
  pass. Writing or changing tests remains separate, explicit scope.

Do not create `PLAN.HUMAN.md`. `PLAN.md` is the sole plan and execution state.

## 5. Audit and materialize

Before approval:

1. Map every explicit requirement and boundary to the objective, a global decision, or a task.
2. Confirm there are no open decisions, unresolved forecast blockers, unsupported assumptions, placeholders, vague verification gates, duplicate task IDs, missing tasks, or parallel write conflicts.
3. Confirm a fresh executor needs neither this conversation nor repository rediscovery to perform each task.

When amending an executed plan, preserve `DONE` and Results only for tasks whose Goal, Writes, How, and Verification are unchanged. Reset every changed task and every task in later blocks to `PENDING` with empty Results. Remove obsolete tasks, retain stable IDs for unchanged tasks.

In plan mode, call `ExitPlanMode` only after the audit and validation pass. After approval, create `$root/plans/<slug>/`, copy the exact approved staging content to `PLAN.md`, reply `Done`, and stop. Do not execute a task in the materialization turn.

Outside plan mode, ask for approval only after the same audit and validation pass, then write the approved `PLAN.md` directly.

## Halt

Stop and ask for the exact missing decision or evidence when the objective or target plan is ambiguous, required ground truth cannot be established, a forecast blocker cannot be resolved, evidence conflicts with intent, the plan cannot be self-contained, validation fails, materialization fails, or cwd is not a git repository. Never present a partial plan as execution-ready.
