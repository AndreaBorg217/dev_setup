# Subagents

Delegate automatically when the work fits; the user need not ask.

## Routing

- Prefer local custom agents over overlapping built-in or plugin agents.
- Keep dialogue, interpretation, design judgement, and small bounded lookups in
  the main thread. Keep bulk collection there through Context Mode and indexed
  source discovery through CodeGraph.
- Use Haiku `explorer` for repository evidence, `data-reader` for a specified
  read-only query, `researcher` for external sources, and `plan-writer` for
  deterministic plan encoding. They never implement.
- Use Haiku `artifact-writer` for a fully specified, low-risk non-source artifact
  such as documentation rendered from approved facts or static fixture data
  rendered from an approved test matrix.
- Use Sonnet `builder` for source, test logic, configuration, or other semantic
  implementation. Use Sonnet `general-purpose` only when no specialist fits.
  Choose per task; writing a file alone does not require Sonnet.
- Never use `WebSearch` or `WebFetch` in the main thread. Route external research
  through `researcher`.
- Skill discovery is manual and on demand. Do not run a catalogue before a task
  or reject work because matching was not performed. Pass each applicable
  skill's exact name and resolved context to the worker.
- Workers invoke every skill named in their prompt, treat supplied skill context
  as resolved, and stop if a named skill or required context is unavailable.

## Bounds

- Dispatch 1 worker by default and at most 2 for independent work. Run dependent
  work serially; never let 2 agents edit the same file.
- Every agent is a leaf. Do not use nested, continuation, verifier, recovery, or
  replacement agents. A blocked worker returns control to the user.
- Give a read-only worker 1 question, named scope, a stop condition, and a
  1,500-character receipt limit. Keep raw output in its context.
- Make implementation prompts self-contained: objective, permitted writes,
  resolved decisions, constraints, acceptance criteria, applicable Skills and
  context, and at most 1 approved targeted check.
- Batch related lookups. Do not repeat a worker's searches, redispatch the same
  open question, or reread unchanged evidence.

## Tool and output discipline

- Set both `subagent_type` and `model` explicitly. Never dispatch Opus as a
  worker.
- Workers without Context Mode must cap output at the producer. Never return
  full files, logs, SQL, result sets, or build output.
- Code-oriented agents use LSP and the `coding` skill. The orchestrator owns all
  human-facing prose, which follows `Straight_to_the_Point`.
