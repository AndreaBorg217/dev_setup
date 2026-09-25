# Plan bundle schema

New plans use schema 4. `PLAN.md` is a compact manifest that remains immutable
during execution, and each task has one mutable file under `tasks/`. Replace
every placeholder, delete optional bullets or sections that do not apply, and
leave each planning-time `Results:` empty. Read `task-template.md` for the
task-file schema.

`plan-execute` runs 1 `>>`-separated reviewable block per invocation unless the
user explicitly requests uninterrupted execution. For example, `t1 >> [t2, t3]
>> t4` normally needs 3 invocations; the second runs the bracketed tasks
concurrently. Use brackets only for at most 2 mutually independent tasks with
disjoint Writes that do not consume facts or artifacts produced by a sibling.

## Staging and approval format

Before materialization, encode the complete bundle this way. Paths are relative
to `plans/<kebab-name>/`. Include every file exactly once. The content inside
each fence is the exact file content approved and materialized; the wrapper is
not written to the plan directory.

````markdown
# Plan bundle: <Concise plan title>

Target: plans/<kebab-name>/

## File: PLAN.md

```markdown
# <Concise plan title>

Plan schema: 4

## Objective

<Complete intended outcome and acceptance criteria.>

## Repository baselines

- `<repository root>`: fetched `<remote/ref>` at `<commit>` on `<branch>`; worktree `<clean, or exact user-approved pre-existing state>`.

## Boundaries and decisions

- Excluded unless explicitly included below: git operations, deployment, test-file changes, and documentation changes.
- Decision: Verification ownership is <Local running only this task's spec test classes for behaviour-changing code, CI, or Manual>; exhaustive build/test suites run only in CI.
- Decision: <Explicit user choice and its scope>; rejected <principal alternative> because <one-clause reason>.

## Risks and resolutions

- <Prospective failure or ambiguity>: resolved by <user decision or exact evidence>; consequence addressed by <plan constraint/task>.

## Grounded facts

- <Technical fact required by the plan>. Evidence: <re-checkable raw material per `rules/workflow.md` — exact path:line, command/result, configuration, test, data export, curl response, or authoritative source>.

## Test matrix

| Spec requirement | Eligible class | Input/precondition | Expected result | Test/fixture location | Owning task |
| --- | --- | --- | --- | --- | --- |
| <Requirement approved by the user> | <One row per enumerated input class, source, or producer> | <Exact setup> | <Observable result> | <Path> | <full-id> |

## Execution order

Blocks: t1-first-task >> t2-independent-task

## Task index

- `t1-first-task`: `tasks/t1-first-task.md`
- `t2-independent-task`: `tasks/t2-independent-task.md`

## Manual actions

- [ ] <Action only the user can perform.>
```

## File: tasks/t1-first-task.md

```markdown
<Exact task file using task-template.md.>
```

## File: tasks/t2-independent-task.md

```markdown
<Exact task file using task-template.md.>
```
````

`Decision:` bullets, `Grounded facts`, `Test matrix`, and `Manual actions` are
optional only when they do not apply. `Repository baselines` is required; use
`- None — no repository work.` only for a genuinely repository-free plan.
`Risks and resolutions` is also required; use `- None — explicit assumption and
prospective-failure audit found no material risk.` only after performing that
audit. `Assumption:` entries and unresolved-question placeholders are forbidden.
Deployment, git, test-file, and documentation tasks use the same task shape and
appear only when explicitly included under Boundaries and decisions. Do not
repeat task fields or execution state in `PLAN.md`.
