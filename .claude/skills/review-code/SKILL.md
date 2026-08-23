---
name: review-code
description: Review and repair a bounded code change for conformity with rules/coding.md in any programming language. Use for direct code-conformance reviews; not for general bug, performance, architecture, or product review.
---

# Review Code

Treat [the coding rules](../../rules/coding.md) as canonical for every
programming language. Read them fully before each review. Consult the
[BAD/GOOD examples](examples.md) only when a code-level
rule needs concrete interpretation; where an example and the canonical rule
differ, follow the canonical rule.

## Isolation

Perform every review pass in a dedicated `sonnet` `general-purpose` subagent;
the narrower reviewer agent cannot make the required corrections. The
orchestrator must pass the review scope, mode, authorized `Writes`, applicable
requirements, and required checks. In verification mode it must also pass the
original repair paths as the correction scope. The orchestrator must not review
the code itself. When this skill is loaded inside an already delegated review
task, perform the review in that subagent and do not delegate again.

## Scope

Review only the code change named by the request or task. Use the request,
authorized `Writes`, and repository diff to identify the complete change. Do
not attribute unrelated pre-existing work in a dirty worktree to the change.

Inspect enough surrounding code, call sites, tests, configuration, and
repository conventions to distinguish evidence from hypothetical concerns.
Existing code outside the change is context, not a finding, unless the changed
code makes it newly incorrect.

`Writes` defines where repair mode may edit. In verification mode, `Writes` is
`None` and the separately supplied correction scope defines which in-scope
violations the repair pass is responsible for.

## Review

Check the human-reviewable code rules for simplicity, locality, style,
exceptions, and testing.

Challenge every new helper, branch, guard, abstraction, parameter, exception
handler, fallback, retry, comment, dependency, test, and changed file. Retain it
only when the requirement or repository evidence makes it necessary. Confirm
that the change implements the stated behavior directly, follows local
conventions, and has not expanded scope.

Repair mode must run the configured linter, formatter check, type checker, and
full test suite required by the coding rules, discovering the repository commands
when they were not supplied. Verification mode runs only checks explicitly
assigned to it because the orchestrator may rerun them independently. Checks
must not modify out-of-scope files.

Do not invent findings for hypothetical misuse, unreachable states, possible
future requirements, or personal preferences.

## Resolve

- **Repair mode:** this is the default. Find and correct every violation within
  the allowed `Writes`, then repeat the review and required checks until the
  result passes. Do not merely suggest a correction the subagent can safely make.
  Do not add behavior, tests, dependencies, documentation, or files unless they
  are already in scope.
- **Verification mode:** use only for an independent pass after repair. Make no
  changes and return each remaining violation with its rule, exact path and line,
  concrete evidence, and the smallest correction.
- **Blocked:** do not make a correction that requires refactoring unrelated code,
  writing outside the allowed paths, or choosing product behavior or
  architecture. In verification mode, return `FAIL` for a violation within the
  correction scope; return `BLOCKED` only when resolving it requires one of
  those prohibited changes or decisions.

## Result

Return `BLOCKED` with the exact missing decision, evidence, or required scope
when a correction cannot proceed under the contract. Return `PASS` only when no
in-scope violation remains and every required check succeeds. In repair mode, do
not return a correctable violation: make the change. In verification mode,
return `FAIL` with numbered violations separated by `---` and ordered by
descending impact when any remain. Include the reviewed scope and commands run.
Return the result directly.
