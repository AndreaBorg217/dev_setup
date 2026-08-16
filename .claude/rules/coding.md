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

- Before writing new code, check in this order and stop at the first one that holds: does this need to exist at all (YAGNI)? Does the codebase already do this? Does the standard library solve it? Does the platform provide it natively? Is there already an installed dependency that covers it? Only add a new dependency if none of the above satisfy the requirement elegantly.
- Prefer the smallest implementation that correctly solves the stated problem. Do not add abstraction, configuration, or generality that wasn't asked for.

## Naming

- Use descriptive names for variables, functions, classes, and files. Avoid unclear single-letter names and abbreviations.
- Choose distinctive names that communicate purpose and role.

## Testing

- Do not create or modify test files unless the user explicitly requests or approves that scope. Running existing tests is verification and does not require separate approval.
- When writing tests, assume the implementation may be wrong rather than writing tests that merely confirm current behavior.
- Get expectations from the accepted specification or explicit request, not from the implementation or its current outputs alone. If intended behavior remains materially ambiguous after repository research, ask before writing tests.
- Prefer real-world data supplied for the task. If none is available, use clearly-labelled synthetic data unless representativeness would materially affect correctness.
- Ask for clarification when an invariant or edge case has ambiguous behavior that would affect correctness - not for every stylistic uncertainty.
- Do not disable failing tests or modify them just to pass without approval.
- Each test must protect observable behavior against a plausible regression or specification breach.
- Each test should be structured with the Arrange-Act-Assert pattern and describe what behaviour it is protecting.

## Exceptions

- Catch specific exceptions. Do not swallow exceptions with generic catch-all handling.
- Unless directed, let unexpected exceptions throw.
- Exception handling is for unplanned error recovery, not branches the code should already plan for. Use `if`/`else` or guard clauses. This doesn't forbid idiomatic EAFP patterns (e.g. Python's `try/except KeyError` for dict or attribute access) - the rule targets using exceptions to skip validation you could reasonably do upfront, not language idioms.

## Code Style

- Add comments only for non-obvious reasoning that future maintainers need to avoid repeating a mistake or investigation. Never restate what the code already says.
- Every public/exported function needs a docstring covering purpose, parameters, return value, and side effects such as exceptions raised. Private/internal helpers only need one if their behavior isn't obvious from the name and signature.
- Avoid ternary operators; prefer explicit `if`/`else`.
- Avoid nested `if`/`else` blocks but rather you must keep conditional checks linear and short favouring the early `return`/`throw`.
- Extract non-obvious domain values and arbitrary literals from business logic into named constants, enums, or environment configuration. Do not create constants for self-explanatory literals.
- Avoid method chaining in business logic, including `map` or `reduce`, when a simple loop is easier to read and debug. This does not apply to idiomatic Flink, Kafka Streams, or Spark pipelines.
- Prefer code that a developer can trace step by step with a breakpoint. If doing so impractical, the solution is too clever and should use more primitive coding constructs.

## Verification

- Run the project's configured linter, formatter check, and type-checker, when present, before considering a change complete. Do not let a formatter rewrite files outside the approved scope (meaning a file that is currently not in git diff).
- If no linter is configured for the language, say so and suggest installing one appropriate for the stack - don't skip the step silently.
- Run the full test suite once a task is complete in its entirety. Don't re-run it after every incremental edit mid-task.
