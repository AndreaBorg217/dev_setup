---
name: coding
description: Mandatory for programming work in any language, including reading or changing source, debugging, code review, tests, builds, linting, type checking, porting or refactoring code between frameworks or languages, and code-oriented LSP use. Do not use for documentation-only or configuration-only work with no program logic.
---

# Coding

Load this skill before any code-facing tool. Keep it active for the task. Read
[examples.md](examples.md) only when a rule needs a concrete BAD/GOOD example.

## Simplicity

Code is not free. Every line is a liability and a potential failure point — conditionals especially, since each one is a branch that must be individually understood, tested, and kept correct. Implement the stated requirement as directly and simply as possible, for a human reviewer and debugger, not for an agent. Treat the task as the complete specification unless the repository provides concrete evidence otherwise.

Before adding code, check in order:

1. Does this need to exist (YAGNI)?
2. Does the codebase already solve it?
3. Does the standard library or platform solve it?
4. Does an installed dependency solve it?
5. Only then add something new.

Additional logic requires evidence that you checked 1-4 before settling on 5, not imagination. Requirements, call sites, tests, this repository's established conventions, and observed runtime conditions are evidence. Hypothetical callers, misuse, edge cases, future requirements, and general framework or industry idiom you were trained on are not evidence — even when the destination framework's own documentation or tutorials treat them as standard — unless they are explicitly requested or already present in this repository.

Unless explicitly required:

- Do not add validation, guards, fallbacks, retries, compatibility code, configuration, extension points, wrappers, or generality.
- Trust invariants guaranteed by construction — a schema field's declared nullability, a type signature, a database constraint, or validation already performed upstream all guarantee a property without needing to be re-checked. Do not guard against unreachable states.
- Do not create an abstraction for a single concrete implementation without my approval.

If two implementations satisfy the requirement, prefer the one with fewer concepts, branches, files, and lines — do not express in 1000 lines what can be expressed in 10. Deleting unnecessary code is preferred.

Even if a bug is identified, do not first assume the code is missing logic and add more code to cater for a particular case. Identify if the bug is in the existing logic and favour amending the existing logic instead of adding more logic to cover bugs.

Do not add handling for established invariants to protect against things that cannot materialise in practice, like:

- Code running `SELECT` queries does not need protection against `DELETE`.
- A collection known to be non-empty does not need an empty guard.
- An established invariant does not need repeated validation — a schema field declared non-nullable, a type marked non-optional, or a database `NOT NULL` constraint does not need an `if x is not None` check before use.

## Style

Once logic is justified under Simplicity, express it plainly:

- Use descriptive names and avoid unclear abbreviations. Avoid `item` when a parameter is a `table_name` or `agg` when an aggregate is `minTimestamp`.
- Prefer explicit intermediate variables when they aid debugging.
- Prefer simple loops over `map`, `reduce`, dense comprehensions, or method chains when easier to follow.
- Avoid clever reflection, dynamic dispatch, or language-specific tricks unless they materially simplify the code.
- Prefer linear conditionals and early returns over nesting.
- Avoid ternaries except for simple assignments.
- Always use braces for `if`/`for`/`while`, even for single-line bodies.
- Group and space the lines. Put related lines together. Order them the way they run. Add blank lines between steps. Keep one idea per line. When a function has 3+ distinct checks, use brief `//` section headers to mark them and split compound conditions into explicit intermediates so each block reads at a glance.
- Simplicity means low cognitive load, not minimum character count.
- Create constants only when the name adds domain meaning or a value must stay synchronized across multiple places.

## Reference Style

If the user supplies their own code, a skeleton of how they think the code should look, or existing code that the task asks you to port, translate, or migrate, treat it as the style and behavior contract for the task, ahead of general language or framework idiom.

- Preserve behavior line-for-line unless the task explicitly asks for a change.
- Add only what the destination mechanically requires to run: a task decorator, an entry point, a changed function signature, a required dependency declaration.
- Do not add retries, callbacks, alerting, structured logging, config, validation, or defensive error handling that was not in the source — even when it is standard in the destination's own documentation or examples — unless the source already had it or the task explicitly requests it.
- If a destination constraint forces a genuine behavior change (for example, a size limit on data passed between steps), name the constraint and make the minimal accommodation for it. Do not use it as license to add unrelated hardening.

## Comments

- Add comments only for stable, non-obvious reasoning: why a decision exists, why an obvious alternative failed, or context another developer could not infer from the code.
- Do not comment on control flow, values, types, or behavior already expressed by the code; those comments drift.
- Update or remove comments and docstrings in the same change when their behavior, assumptions, or constraints change.

## Locality & Abstraction

- Prefer code that can be understood and debugged at the call site. Five obvious lines inline are usually better than a five-line helper used once.
- Extract a helper only when logic is genuinely reused, its name materially improves understanding, or leaving it inline makes the containing function difficult to follow.
- Do not introduce interfaces, factories, strategies, adapters, base classes, configuration objects, or similar abstractions for theoretical reuse. "Clean code", separation of concerns, testability, and possible future requirements are not sufficient reasons.
- A small amount of obvious duplication is preferable to abstraction that increases cognitive load. The cleanest code is the easiest to debug not the one that looks the most engineered.

## Exceptions

Catch specific exceptions only when meaningful recovery is required. Otherwise let unexpected exceptions propagate.

Do not swallow exceptions, turn programmer errors into fallback values, log and immediately rethrow without adding useful context, or add retry logic without evidence that retries are needed.

Use normal conditionals for expected control flow. Idiomatic EAFP is fine when it is genuinely simpler.

## Testing

Do not create or modify tests unless explicitly requested or approved.

Each test must validate one observable behavior with a plausible failure path, derive expectations from the specification rather than the implementation, and protect against a realistic regression. In this way, a condition in the code is either a case that can materialise in reality and should be protected by tests, or otherwise it cannot materialise in reality and hence it should be removed and not covered by a test to add coverage.

Use Arrange-Act-Assert. Do not test impossible behavior, language/framework behavior, trivial getters/setters, constants, or wiring merely for coverage.

Prefer supplied real-world data; otherwise use clearly labelled synthetic data unless representativeness affects correctness.

Do not disable or weaken failing tests without permission.

## Scope

Change only what is necessary for the requested task.

Do not perform opportunistic refactors, rename or reformat unrelated code, reorganize modules unnecessarily, clean up unrelated code, or silently expand scope.

Remove code made unused or unreachable by the current change. Do not leave commented-out implementations. Mention pre-existing dead code outside the task scope instead of removing it.

Follow relevant repository conventions, but do not copy an abstraction merely because an example exists elsewhere.

Mention unrelated problems rather than fixing them without approval.

## Discovery and context (token budget)

Spend tokens on answers, not on discovery. Discovery order is fixed:

1. CodeGraph for source: call `codegraph_explore` FIRST for how
   something works, architecture, call flows, where/what a symbol is,
   surveying an area, or before editing a symbol. Its returned source
   is Read-equivalent: treat it as already Read and do NOT re-open
   those files. One call is usually enough; stop there.
2. Context Mode sandbox for data: GATHER with `ctx_batch_execute`,
   FOLLOW-UP with one batched `ctx_search`, PROCESS with
   `ctx_execute`/`ctx_execute_file` (always pass `intent` when output
   may exceed ~5KB). Fetch URLs with `ctx_fetch_and_index`, never
   `WebFetch`. Analyse large files, logs, or command output in the
   sandbox, never with native `Read`/`Bash`/`Grep` loops.
3. LSP for type intelligence: definitions, references, symbols, type
   info, and diagnostics during exploration and implementation.
4. Native tools last: `rg` only for exact strings, configs, or
   non-symbolic content LSP and CodeGraph could not answer; `Read`
   only for exact bytes needed for an edit; `Bash` only for short
   fixed-output commands.

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

When a language server is available for the language being edited, use it for type-aware navigation and diagnostics (definitions, references, symbols, type information, errors) after the CodeGraph/Context Mode pass above. Treat language-server results as code intelligence, not as a substitute for the repository's configured verification commands. Run verification commands themselves inside `ctx_execute` with an `intent` filter so only failures and summaries enter context.

If no linter exists, say so and suggest an appropriate one.

## Final Audit

Before presenting the diff, reread it once as a reviewer rather than its author.

- Every helper, branch, guard, abstraction, parameter, exception handler, retry, callback, default value, log statement, comment, and dependency must trace to a requirement, a call site, a test, this repository's convention, or an observed failure — not to what the destination framework typically looks like.
- If the task was a port or translation, confirm nothing was added beyond what the destination mechanically requires.
- If the user supplied their own code as an example, confirm the result matches its style rather than general idiom.

Remove anything that fails this check.
