# Workflow

- Investigate before asking. Read the relevant code, tests, configuration, and dependency manifests first. Repository facts discoverable with a bounded search are research, not user questions; raise contradictions in the evidence instead of silently choosing one.
- Ask only for unresolved user-owned decisions when a wrong assumption would materially change or discard the work. Include a recommended default.
- Scale ceremony to blast radius. Let small changes with one obvious correct form proceed directly. Make assumptions, boundaries, and verification explicit for multi-step work and for changes involving schemas, authentication, money, migrations, deletion, or other high-risk state.
- Structure implementation as a sequence of small, coherent edits that are easy to review.
- Treat one reviewable unit as one logical behavior, design decision, or structural element. Examples include an OOP class skeleton with its fields, constructor, and required getters/setters; one function or cohesive method; or one Airflow task.
- Keep each unit to roughly 25-30 lines of code at most. If a unit would exceed that, split it at a natural boundary before editing.
- Order edits so drift from the expected design or behavior can be caught and corrected locally instead of requiring a later broad refactor or another implementation session.
- Do not start broad refactors unless explicitly directed.
- Keep work surgical and limited to the requested behavior and named files. Do not fix adjacent problems. If the task genuinely requires touching more, ask before expanding scope.
- If repository evidence invalidates an established assumption or approach, stop and explain the conflict instead of quietly improvising a different design.
- On unrecoverable error or deny, stop immediately and ask the user rather than retrying the same operation.
