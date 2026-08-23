# Coding

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
- Add comments only for non-obvious reasoning: why a decision exists, why an obvious alternative failed, or context another developer could not infer from the code.
- Correct or remove stale comments and docstrings when editing nearby code.

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

Follow relevant repository conventions, but do not copy an abstraction merely because an example exists elsewhere.

Mention unrelated problems rather than fixing them without approval.

## Verification

Before completion, run the configured linter, formatter check, type checker, and full test suite.

Do not let formatters modify files outside the current scope. During development, use the smallest relevant verification commands rather than repeatedly running the full suite.

If no linter exists, say so and suggest an appropriate one.

Before finishing, review each new helper, branch, guard, abstraction, parameter, exception handler, fallback, comment, and dependency. If no requirement or repository evidence requires it, remove it. Every extra line of code is a penalty which we will need to maintain and potentially debug if it fails.

## Git

- Match the repository's existing commit convention.
- Keep commits small, logical, and reviewable.
- Amend fixes into the commit they belong to rather than adding fixup commits: `git commit --amend --no-edit`.
- Split unrelated or independently meaningful work into separate commits.
- Rebase onto the target branch instead of merging it: `git fetch origin && git rebase origin/main`.
- Keep final history linear and remove meaningless false starts or "address review" commits.
- Rewrite local history with interactive rebase when needed: `git rebase -i main`.
- After use `git push --force-with-lease origin BRANCH-NAME`, never plain `--force`.
- Commit locally as useful, but push in bulk to avoid unnecessary CI/CD churn.
