# Workflow

- Investigate before asking. Read the relevant code, tests, configuration, and dependency manifests first. Repository facts discoverable with a bounded search are research, not user questions; raise contradictions in the evidence instead of silently choosing one.
- Ask only for unresolved user-owned decisions when a wrong assumption would materially change or discard the work. Include a recommended default.
- Scale ceremony to blast radius. Let small changes with one obvious correct form proceed directly. Make assumptions, boundaries, and verification explicit for multi-step work and for changes involving schemas, authentication, money, migrations, deletion, or other high-risk state.
- Implement tasks in atomic units of work that could map cleanly to commits.
- When a unit of work is complete, pause and ask me to review and commit before proceeding to the next unit.
- Do not start broad refactors unless explicitly directed.
- Keep work surgical and limited to the requested behavior and named files. Do not fix adjacent problems. If the task genuinely requires touching more, ask for approval before expanding scope.
- If repository evidence invalidates an approved assumption or approach, stop and explain the conflict instead of quietly improvising a different design.
- On unrecoverable error or deny, stop immediately and ask the user rather than retrying the same operation.
