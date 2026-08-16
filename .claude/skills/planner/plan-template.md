# PLAN.md schema

Use this literal structure for `plans/<kebab-name>/PLAN.md`. Replace every placeholder, delete optional bullets or sections that do not apply, and leave each planning-time `Results:` empty.

```markdown
# <Concise plan title>

Plan schema: 1

## Objective

<Complete intended outcome and acceptance criteria.>

## Boundaries and decisions

- Excluded unless explicitly included below: git operations, deployment, test-file changes, and documentation changes.
- Existing tests, lint, builds, and artifact checks may be run for verification.
- Assumption: <Specific, falsifiable, user-approved constraint>; if false, <effect on the plan>.
- Decision: <Selected option>; rejected <principal alternative> because <one-clause reason>.

## Grounded facts

- <Technical fact required by the plan>. Evidence: <exact path:line, command/result, configuration, test, or authoritative source>.

## Execution order

Blocks: t1-first-task >> t2-independent-task

## Tasks

### t1-first-task
Status: PENDING
Model: sonnet
Goal: <One-sentence outcome.>
Writes: <Comma-separated paths/globs, or None.>
How: <Self-contained implementation steps, exact paths and commands, and important function/type/interface signatures.>
Verification: <Observable artifact assertion.>
Results:

### t2-independent-task
Status: PENDING
Model: haiku
Goal: <One-sentence outcome.>
Writes: None
How: <Self-contained mechanical work.>
Verification: <Observable artifact assertion.>
Results:

## Manual actions

- [ ] <Action only the user can perform.>
```

`Assumption:` and `Decision:` bullets, `Grounded facts`, and `Manual actions` are optional. Deployment, git, test-file, and documentation tasks use the same task shape and appear only when explicitly included under Boundaries and decisions.
