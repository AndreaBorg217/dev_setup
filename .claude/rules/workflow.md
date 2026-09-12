# Workflow

- Investigate before asking. Gather only the evidence relevant to this edit via targeted CodeGraph/Context Mode lookups. Repository facts discoverable with a bounded search are research, not user questions; raise contradictions instead of silently choosing one. Do not pre-read full test/configuration manifests for surgical edits.
- Ask only for unresolved user-owned decisions when a wrong assumption would materially change or discard the work. Include a recommended default.
- Scale ceremony to blast radius. Let small changes with one obvious correct form proceed directly. Make assumptions, boundaries, and verification explicit for multi-step work and for changes involving schemas, authentication, money, migrations, deletion, or other high-risk state.
- Structure implementation as small, coherent, reviewable behaviours or design
  decisions. Split only at natural boundaries, not arbitrary line counts.
- Do not start broad refactors unless explicitly directed.
- Keep work surgical and limited to the requested behavior and named files. Do not fix adjacent problems. If the task genuinely requires touching more, ask before expanding scope.
- If repository evidence invalidates an established assumption or approach, stop and explain the conflict instead of quietly improvising a different design.
- On a denied operation, correct a malformed or over-broad request once when the
  same permitted action is clear. Otherwise report the denial and stop. Never
  enter a retry, recovery, or replacement-worker loop.
- End an exhaustive investigation with a bounded evidence artifact or receipt.
- At discovery -> planning, approved plan -> implementation, and implementation
  -> extended review, provide a concise ready-to-paste handoff containing the
  objective, decisions, evidence or artifact paths, current state, and next
  action. Recommend a fresh session at these boundaries. Recommend `/compact`
  when continuing the same phase and `/clear` when the objective changes. The
  user decides whether to switch sessions.
