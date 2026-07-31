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
- Ask for clarification when an invariant or edge case has ambiguous behavior that would affect correctness - not for every stylistic uncertainty.
- Do not disable failing tests or modify them just to pass without approval.

## Exceptions

- Do not swallow exceptions with generic catch-all handling.
- Catch specific exceptions.
- Unless directed, let unexpected exceptions throw.
- Exception handling is for unplanned error recovery, not branches the code should already plan for.
- Do not use exceptions for control flow. Use `if`/`else` or guard clauses. This doesn't forbid idiomatic EAFP patterns (e.g. Python's `try/except KeyError` for dict or attribute access) - the rule targets using exceptions to skip validation you could reasonably do upfront, not language idioms.

## Code Style

- Comments explain why, not what - the reasoning behind a decision, not a restatement of the code. Why this approach and not the obvious alternative, what was tried and abandoned, and why. That reasoning only survives as long as someone's memory of it, or an agent's context window - a few weeks for a person, one session for an agent. Undocumented, the next person or the next agent either remakes the same wrong choice or spends a week rediscovering it.
- Only add inline comments for non-trivial decisions that need justification. Don't comment what the code already makes obvious.
- Every public/exported function needs a docstring covering purpose, parameters, return value, and side effects such as exceptions raised. Private/internal helpers only need one if their behavior isn't obvious from the name and signature.
- All files must end with a trailing newline.
- Avoid ternary operators; prefer explicit `if`/`else`.
- Avoid nested `if`/`else` blocks but rather you must keep conditional checks linear and short favouring the early `return`/`throw`.
- Never use magic numbers or hardcoded strings inside business logic. Extract all arbitrary values into named constants at the top of the file or enums or into an environment configuration.

## Verification

- Always run the project's configured linter (and formatter/type-checker, if present) before considering a change complete.
- If no linter is configured for the language, say so and suggest installing one appropriate for the stack - don't skip the step silently.
- Run the full test suite once a task is complete in its entirety. Don't re-run it after every incremental edit mid-task.
