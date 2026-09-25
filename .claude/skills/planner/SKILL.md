---
name: planner
description: Use when the user asks to plan or scope multi-step work before implementation. Resolves decisions through user answers or technical evidence, then produces a split plan bundle for plan-execute.
when_to_use: "plan multi-step work, scope before implementation, PLAN.md, task graph, plan-execute, plan-template.md, task-template.md, approval brief, decision register, resolved by evidence, resolved by user, AskUserQuestion, design probe, artifact-writer, explorer worker, reviewer agent, Blocks:, Skills:, Skill context:, Materialization, Handoff:, Verification: CI, Verification: Manual, Verification: Local, test matrix, materialize_plan_bundle.py, staging bundle, ExitPlanMode, investigation plan, worktree baseline"
model: opus
disable-model-invocation: true
---

# Planner

Run on Opus as a human-in-the-loop orchestrator; the user is the architect, keep grilling them relentlessly until a common ground of understanding has been reached on what the user needs done and a brief skeleton of how it will be done and verified to be correct. The human owns decisions and
spec disambiguation; Opus owns an unambiguous task graph (every task has
resolved skills, agent/model, writes, handoff, and verification — unresolved
context blocks the bundle). Keep the user in control from prompt
interpretation through final approval, own design judgement, use global
routing for bounded evidence, and leave all plan writing, materialization, and
review to existing Haiku agents. Opus plans; it never writes or reviews the plan
artifact. Do not implement or repeat worker investigations.

Produce `plans/<slug>/PLAN.md` plus one `tasks/<full-id>.md` per task. A fresh
Sonnet `plan-execute` session must be able to run it without this conversation.

Before discovery or worker dispatch, read `plan-template.md` and
`task-template.md` completely. They are the canonical schema for the task graph,
approval brief, writer prompt, and review.

## Resolve the work

1. Invoke the `git` skill before repository discovery. Record each repository's
   fetched ref, commit, branch, and approved worktree state as its baseline.
2. Restate the objective, intended outcome, and boundaries. Ask the user to
   correct any material ambiguity before relying on an interpretation. Maintain
   one current objective: a user correction replaces conflicting older scope,
   evidence, and candidate tasks; discovery never expands scope. Do not fill a
   gap in the spec with what you judge best — surface the gap with enough
   context for the user to decide, and record their answer in the register.
   If the user asks for something to be explained as part of the feature (a
   test plan, a review, a walkthrough of the approach), treat that explanation
   as its own task with its own owner and handoff, not as a side effect of an
   implementation task.
3. Resolve repository facts and data queries with bounded workers. Route all evidence gathering — repository reads, MCP queries, external sources — through `explorer` workers. Never run MCP queries or data lookups in the main thread between subagent batches; batch unresolved questions and re-delegate them together. Consult only the domain skills relevant to this objective and record each used skill's exact `name` and resolved context. Run a full inventory of available skills only for cross-cutting or ambiguous scopes.
4. Maintain an explicit register of decisions, assumptions, doubts, missing
   contracts, conflicting conventions, compatibility concerns, and
   external-state risks. Mark each item `resolved by evidence`, `resolved by
user`, or `open`. Resolve technical facts from evidence and consult the user
   on preferences, trade-offs, standards, and any choice that changes the
   outcome. Batch at most 3 related questions and never treat silence as a
   decision. A `resolved by evidence` item requires verifiable evidence per
   `rules/workflow.md` — re-checkable raw material such as query/command text
   plus its output, a data export, a curl response, or a path:line citation.
   Numbers inherited from prior plans, HANDOFFs, or studies must be re-run
   live via `explorer` before a decision uses them. Each metric must state
   what it counts (population, filters, numerator/denominator).
5. Use one Sonnet design probe only when architecture, stateful processing,
   generated contracts, migrations, or cross-repository sequencing needs
   semantic resolution. It must return a concrete API or artifact handoff, not
   another open investigation. Halt if a required probe remains inconclusive
   or unavailable; do not proceed to drafting on an unresolved probe.
6. Ask the user via `AskUserQuestion` whether review is in scope for this plan.
   Recommend a default: `yes` for multi-file, risky, or schema/auth/migration-
   touching plans; `no` for small single-file mechanical work. Record the
   answer as a `resolved by user` item in the register.

Before drafting, audit scope, contracts, configuration precedence,
compatibility, rollout, rollback, tests, repository state, dependencies, and
handoffs. Continue the evidence-and-user-dialogue loop until the register has no
open item and the plan has no known gap. Do not claim certainty about unknowable
future events; instead make every material uncertainty an explicit resolved
decision, mitigation, validation step, or blocker. A plan cannot contain an
unresolved assumption, doubt, question, placeholder, or deferred design choice.

An investigation plan is valid. Define its questions, evidence sources, stop
conditions, output artifact or handoff, and validation criteria; do not force
feature implementation or irrelevant tests into it.

## Design the task graph

Follow both templates exactly when designing the task graph and writing the
approval brief. Pass both template paths to `artifact-writer` so it can encode
the bundle faithfully. Apply these invariants:

- Use stable task IDs and give each writable path exactly one owner. Each task
  leaves a coherent artifact and does not rely on a later repair.
- Choose the least expensive capable model per task and record a concrete
  `Model reason` — this implies the worker (`Haiku`→`explorer`/`artifact-writer`, `Sonnet`→`builder` per `rules/subagents.md`). Use Haiku for bounded deterministic work with complete inputs,
  including read-only collection, approved documentation rendering, and static
  fixture data from an approved test matrix. Use Sonnet for semantic judgement,
  source or test logic, runtime configuration, debugging, ambiguity, and
  elevated-risk work. A write alone does not determine the model.
- Verify referenced existing paths and symbols. Trace generated or shared
  contracts through production, materialization, and their first consumer; do
  not plan reflection, adapters, or fallbacks around missing contracts.
- Encode dependencies once in `Blocks:`. Bracket at most 2 independent tasks
  with disjoint writes and no sibling-produced input.
- Keep shared evidence and decisions in `PLAN.md`; keep only execution-critical
  details in each task. Do not copy source, logs, or discovery narrative.
- Recommend exact applicable skills (`name` from `SKILL.md:2`) and resolved `Skill context:` per `task-template.md:14-15` — unresolved context blocks the bundle. Include git, deployment, tests, or documentation only when the user included them.
- Declare `Materialization` and `Handoff` when a later task needs locally built,
  installed, generated, published, or migrated state. Consumers run in a later
  block.
- Behaviour-changing code tasks default to `Local` verification running only
  that task's spec test classes; use `Manual` for investigation or
  documentation. Full suites belong to CI.
- When review is in scope (step 6 above resolved `yes`), add one task owned by
  the read-only Sonnet `reviewer` agent, with a stable ID like any other task.
  Place its `Blocks:` after the implementation task(s) it reviews. Set
  `Skills: None` (the `reviewer` agent is self-contained) and
  `Verification: Manual` — a human reads the reviewer's findings; it is not an
  automated pass/fail gate. Set `Handoff:` to instruct `plan-execute` to
  surface the reviewer's returned findings to the user before considering the
  overall plan complete.

For behaviour changes, decompose each spec requirement over its full eligible
domain — every input class, source, and producer enumerated from code
evidence, such as listing every mapper or handler the requirement applies to.
An unenumerated domain is an open register item, not an assumed pass. Add a
test matrix with one row per eligible class naming the spec requirement, the
class, precondition, expected result, test location, and owning task. The
most important question for any task is how its logic will be verified as
correct: every task needs a concrete verification path, not just a completion
criterion.

## Approve the brief

Before calling `artifact-writer`, show the user a concise but complete approval
brief containing:

- your interpretation of the prompt, objective, outcome, and boundaries;
- every material decision, assumption, doubt, risk, and resolution;
- ordered tasks with model, model reason, outcome, and dependencies;
- the implementation plan, or the evidence and synthesis plan for an
  investigation; and
- the test plan with scenarios and verification ownership, or an explicit
  reason tests do not apply.

Ask the user to identify omissions, incorrect assumptions, or desired changes.
Incorporate each correction, reopen any affected decisions and downstream
tasks, and present the revised brief. Repeat until the register has no open item
and the user explicitly approves the complete brief. Do not infer approval and
do not write the bundle before it.

## Write and validate

After approval, dispatch one Haiku `artifact-writer` with the approved brief,
staging path, repository roots, evidence, skill context, both template paths,
and the validation command below. It writes the complete staging bundle once
without changing the design and runs the deterministic check:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/materialize_plan_bundle.py" \
  "<staging-file>" --repo-root "$root" --check
```

Then dispatch one read-only Haiku `explorer` to review the staging bundle against
the approved brief, both templates, and the validator result. It returns only
specific mismatches; it does not redesign or write. Send a structural mismatch
back to `artifact-writer` once. A semantic mismatch returns to user dialogue.
Do not load the bundle into Opus and do not create verifier or recovery agents.

## Approve and materialize

After review, dispatch the same Haiku `artifact-writer` to copy the checked
staging bundle unchanged to the harness plan file in plan mode and validate it.
Outside plan mode, the brief approval authorizes the writer to materialize the
checked bundle. Materialize without regeneration:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/materialize_plan_bundle.py" \
  "<staging-file>" --repo-root "$root"
```

Reply `Done` and stop before implementation. When amending, retain `DONE` only
for tasks whose full contract is unchanged; reset changed and downstream tasks
and remove obsolete task files.

Before `ExitPlanMode`, confirm every template was read, the Haiku writer and
reviewer steps ran, and the validator passed. Halt and do not exit plan mode on
an unread template, a skipped writer/reviewer step, a validator failure, or any
open register item. Never present a partial plan as execution-ready.
