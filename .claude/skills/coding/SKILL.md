---
name: coding
description: Mandatory for programming work in any language, including reading or changing source, debugging, code review, tests, builds, linting, type checking, and code-oriented LSP use. Do not use for documentation-only or configuration-only work with no program logic.
---

# Coding

Load this skill before any code-facing tool. Keep it active for the task. Read
[examples.md](examples.md) only when a rule needs a concrete BAD/GOOD example.
Use the global routing in `rules/subagents.md`: keep code judgement and edits on
Sonnet, and send broad/noisy read-only evidence gathering to a bounded local
Haiku agent.

## Code intelligence and affected tests

When the repository has a `.codegraph/` index, use the `codegraph_explore` MCP
tool before LSP, grep, or direct reads to locate and understand source, call
paths, and blast radius. A subagent or non-MCP session uses the equivalent
`codegraph explore` CLI. The MCP server keeps the shared index fresh; the CLI
also provides focused automation such as `codegraph affected`. Treat returned
line-numbered source as read; use LSP for type-aware navigation and diagnostics,
and use grep/direct reads for configuration, documentation, unsupported files,
or a specific gap in the graph result.

Do not add a session-start or per-edit sync step. The MCP server reconciles the
index when it connects and watches file changes. If a response identifies a
stale file or disabled watcher, read only the named file directly and report
the degraded index state.

Before choosing an authorised targeted test command, pass the changed source
paths to `codegraph affected --stdin --quiet`. `git diff --name-only HEAD`
covers tracked staged and unstaged paths; add relevant untracked source paths
explicitly. Use the result to narrow the test set, not as proof that omitted
tests cannot fail, and preserve any repository-required or user-approved full
suite.

Use Context Mode's MCP tools for sandbox execution and normal in-session
index/search work: `ctx_execute`, `ctx_execute_file`, `ctx_batch_execute`, and
`ctx_search`. Its plugin bundle also contains CLI utilities for index, search,
diagnostics, upgrade, and the status line, but a marketplace install does not
require a separate CLI installation. There is no CLI substitute for the
`ctx_execute*` sandbox tools. Run a noisy CodeGraph CLI command or authorised
test inside a Context Mode MCP call so only derived or searched evidence enters
the conversation.

## Synchronize before source work

For a new repository change workflow, invoke the `git` skill before reading
source for design or editing. Establish branch, worktree, upstream, and
divergence, then fetch the verified remote ref. If synchronization needs pull,
rebase, stash, reset, conflict resolution, or a target/upstream choice, use
`AskUserQuestion` and wait. Do not assume the strategy. When resuming an
approved plan with partial edits, use its recorded baseline instead of fetching
or rebasing through those edits.

## Simplicity

Implement the stated requirement as directly and simply as possible. Treat the task as the complete specification unless the repository provides concrete evidence otherwise.

Before adding code, check in order:

1. Does this need to exist (YAGNI)?
2. Does the codebase already solve it?
3. Does the standard library or platform solve it?
4. Does an installed dependency solve it?
5. Only then add something new.

Additional logic requires evidence that you check up to 1-4 before you settled on 5, not imagination. Requirements, call sites, tests, established repository conventions, and observed runtime conditions are evidence. Hypothetical callers, misuse, edge cases, or future requirements are not.

Unless explicitly required:

- Do not add validation, guards, fallbacks, retries, compatibility code, configuration, extension points, wrappers, or generality.
- Trust invariants guaranteed by construction. Do not guard against unreachable states.
- Do not create an abstraction for a single concrete implementation without my approval.

If two implementations satisfy the requirement, prefer the one with fewer concepts, branches, files, and lines. Deleting unnecessary code is preferred.

Even if a bug is identified, do not first assume the code is missing logic and add more code to cater for a particular case. Identify if the bug is in the existing logic and favour amending the existing logic instead of adding more logic to cover bugs.

## Locality & Abstraction

Prefer code that can be understood and debugged at the call site. Five obvious lines inline are usually better than a five-line helper used once.

Extract a helper only when logic is genuinely reused, its name materially improves understanding, or leaving it inline makes the containing function difficult to follow.

Do not introduce interfaces, factories, strategies, adapters, base classes, configuration objects, or similar abstractions for theoretical reuse. "Clean code", separation of concerns, testability, and possible future requirements are not sufficient reasons.

A small amount of obvious duplication is preferable to abstraction that increases cognitive load. The cleanest code is the easiest to debug not the one that looks the most engineered.

Examples:

- Code running `SELECT` queries does not need protection against `DELETE`.
- A collection known to be non-empty does not need an empty guard.
- An established invariant does not need repeated validation.

## Code Style

Prefer basic constructs that can be traced step by step with a debugger.

- Use descriptive names and avoid unclear abbreviations.
- Prefer explicit intermediate variables when they aid debugging.
- Prefer simple loops over `map`, `reduce`, dense comprehensions, or method chains when easier to follow.
- Avoid clever reflection, dynamic dispatch, or language-specific tricks unless they materially simplify the code.
- Prefer linear conditionals and early returns over nesting.
- Avoid ternaries except for simple assignments.
- Simplicity means low cognitive load, not minimum character count.
- Create constants only when the name adds domain meaning or a value must stay synchronized across multiple places.
- Add comments only for stable, non-obvious reasoning: why a decision exists, why an obvious alternative failed, or context another developer could not infer from the code.
- Do not comment on control flow, values, types, or behavior already expressed by the code; those comments drift.
- Update or remove comments and docstrings in the same change when their behavior, assumptions, or constraints change.

## Exceptions

Catch specific exceptions only when meaningful recovery is required. Otherwise let unexpected exceptions propagate.

Do not swallow exceptions, turn programmer errors into fallback values, log and immediately rethrow without adding useful context, or add retry logic without evidence that retries are needed.

Use normal conditionals for expected control flow. Idiomatic EAFP is fine when it is genuinely simpler.

## Testing

Do not create or modify tests unless explicitly requested or approved.

Each test must validate one observable behavior with a plausible failure path, derive expectations from the specification rather than the implementation, and protect against a realistic regression.

Use Arrange-Act-Assert. Do not test impossible behavior, language/framework behavior, trivial getters/setters, constants, or wiring merely for coverage.

Prefer supplied real-world data; otherwise use clearly labelled synthetic data unless representativeness affects correctness.

Do not disable or weaken failing tests without permission.

## Scope

Change only what is necessary for the requested task.

Do not perform opportunistic refactors, rename or reformat unrelated code, reorganize modules unnecessarily, clean up unrelated code, or silently expand scope.

Remove code made unused or unreachable by the current change. Do not leave commented-out implementations. Mention pre-existing dead code outside the task scope instead of removing it.

Follow relevant repository conventions, but do not copy an abstraction merely because an example exists elsewhere.

Mention unrelated problems rather than fixing them without approval.

## Verification

During implementation, use LSP/static diagnostics and only the smallest
targeted check authorised by the task. Do not run a full build or test suite
after individual edits. A model session may run one full suite per repository
and test runner at the final pre-MR state, after hook/user approval; CI owns it
otherwise.
If runtime-relevant source changes after that run, a second run requires a new
user decision. Documentation, comment, formatting-only Python, and docstring-only
changes do not require runtime tests and do not invalidate a completed suite.

Do not let formatters modify files outside the current scope. Run configured
linters, formatter checks, and type checkers only when the task or user approves
them.

When a language server is available for the language being edited, use it during exploration and implementation. Prefer language-server navigation and diagnostics for definitions, references, symbols, type information, and errors; use text search for non-symbolic content or when the language server cannot answer the query. Treat language-server results as code intelligence, not as a substitute for the repository's configured verification commands.

If no linter exists, say so and suggest an appropriate one.

Before finishing, review each new helper, branch, guard, abstraction, parameter, exception handler, fallback, comment, and dependency. If no requirement or repository evidence requires it, remove it. Every extra line of code is a penalty which we will need to maintain and potentially debug if it fails.

## Code review

Review only the requested change. Use the request, permitted writes, and diff to
separate it from unrelated dirty-worktree changes. Inspect enough surrounding
code, call sites, tests, configuration, and local conventions to distinguish
evidence from hypothetical concerns.

Challenge every new helper, branch, guard, abstraction, parameter, exception
handler, fallback, retry, comment, dependency, test, and changed file. Do not
invent findings for hypothetical misuse, unreachable states, future
requirements, or personal preferences.

When repair is authorised, fix every in-scope violation and rerun only the
declared targeted verification. When review is read-only, report each violation
with its rule, exact path and line, concrete failure case, and smallest
correction. Return `PASS` only when no in-scope violation remains; return
`BLOCKED` when correction requires a user decision or writes outside scope.
