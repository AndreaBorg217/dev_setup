---
paths:
    - "**/*.py"
    - "**/*.ts"
    - "**/*.tsx"
    - "**/*.js"
    - "**/*.jsx"
    - "**/*.go"
    - "**/*.sh"
    - "**/*.bash"
    - "**/*.rb"
    - "**/*.java"
    - "**/*.rs"
---

# Coding

## Simplicity & Dependencies

- Before writing new code, check in this order and stop at the first one that holds: does this need to exist at all (YAGNI)? Does the codebase already do this? Does the standard library solve it? Does the platform provide it natively? Is there already an installed dependency that covers it?
- Only add a new dependency if none of the above satisfy the requirement elegantly.
- Prefer the smallest implementation that correctly solves the stated problem. Do not add abstraction, configuration, or generality that wasn't asked for.
- Being lazy about the solution doesn't mean being lazy about correctness: input validation at trust boundaries, data-loss handling, security, and accessibility are never cut for the sake of brevity.

## Testing

- When writing tests, assume the implementation may be wrong rather than writing tests that merely confirm current behavior.
- Get expectations from the specification, not from reading the implementation or its current outputs. If no written spec exists, ask what the intended behavior is rather than inferring it from the code.
- Where possible, ask for real-world data rather than inventing test data. If none is available, use clearly-labeled synthetic data instead of stalling on the task.
- Ask for clarification when an invariant or edge case has ambiguous behavior that would affect correctness — not for every stylistic uncertainty.
- Do not disable failing tests or modify them just to pass without approval.

## Exceptions

- Do not swallow exceptions with generic catch-all handling.
- Catch specific exceptions.
- Unless directed, let unexpected exceptions throw.
- Exception handling is for unplanned error recovery, not branches the code should already plan for.
- Do not use exceptions for control flow. Use `if`/`else` or guard clauses. This doesn't forbid idiomatic EAFP patterns (e.g. Python's `try/except KeyError` for dict or attribute access) — the rule targets using exceptions to skip validation you could reasonably do upfront, not language idioms.

## Code Style

- Comments explain why, not what — the reasoning behind a decision, not a restatement of the code. Why this approach and not the obvious alternative, what was tried and abandoned, and why. That reasoning lives in someone's head for a few weeks after the decision is made and then it's gone; the next person touching the code either remakes the same wrong choice or spends a week rediscovering it. AI-generated code has no memory of that reasoning at all, so writing it down matters more now, not less.
- Only add inline comments for non-trivial decisions that need justification. Don't comment what the code already makes obvious.
- Every public/exported function needs a docstring covering purpose, parameters, return value, and side effects such as exceptions raised. Private/internal helpers only need one if their behavior isn't obvious from the name and signature.
- All files must end with a trailing newline.
- Avoid ternary operators; prefer explicit `if`/`else`.
- Python's `or` idiom is allowed as a default-substitution shorthand (`x = a or default`), but only when any falsy value should be treated as equivalent to missing. If `a` can legitimately be a valid falsy value (`0`, `""`, `[]`, `False`), use `x = a if a is not None else default` instead.

## Verification

- Always run the project's configured linter (and formatter/type-checker, if present) before considering a change complete.
- If no linter is configured for the language, say so and suggest installing one appropriate for the stack — don't skip the step silently.
- Run the full test suite once a task is complete in its entirety. Don't re-run it after every incremental edit mid-task.
