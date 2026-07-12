# Coding

## Testing

- When writing tests, assume the implementation may be wrong rather than writing tests that merely confirm current behavior.
- Where possible, ask for real-world data rather than inventing test data.
- Ask for clarification when an invariant or edge case has ambiguous or unexpected behavior.
- Get expectations from the specification, not from reading the implementation or its current outputs.
- Do not disable failing tests or modify them just to pass without approval.

## Exceptions

- Do not swallow exceptions with generic catch-all handling.
- Catch specific exceptions.
- Unless directed, let unexpected exceptions throw.
- Exception handling is for unplanned error recovery, not branches the code should already plan for.
- Do not use exceptions for control flow. Use `if`/`else` or guard clauses.

## Code Style

- Use comments to explain why, not what.
- Only add comments for non-trivial decisions that require justification.
- All files must end with a trailing newline.
- Avoid ternary operators in all languages.
- Python's `or` idiom is allowed, for example `x = a or default`.
