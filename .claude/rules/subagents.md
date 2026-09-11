# Subagents

Delegate automatically when the work fits; the user need not ask. The main
thread is a thin orchestrator: fan out, then fan in receipts only.

## When to delegate

- The work has an explicit objective, scope, and acceptance check.
- Collection is noisy or menial and the main thread needs only derived facts,
  not raw output (review comments, logs, multi-file scans).
- The work splits into independent units with disjoint writes (per repository,
  per file set, per MR). Run those concurrently; serial execution that bloats
  main-thread context is a routing defect.
- Keep dialogue, design judgement, and follow-up decisions in the main thread.
  Interpretation stays with the caller unless the caller supplied the grouping
  categories.

## Routing

- Prefer local custom agents over overlapping built-in or plugin agents.
- Use Haiku `explorer` for all read-only collection: repository evidence, a
  specified data query, or external sources. It never implements.
- Use Haiku `artifact-writer` for fully specified renders and mechanical edits:
  documentation from approved facts, static fixture data from an approved test
  matrix, deterministic plan encoding, and low-risk mechanical config edits. It
  runs only supplied commands and never takes source logic, test logic,
  debugging, or unresolved content decisions.
- Use Sonnet `builder` for source, test logic, configuration with semantic
  risk, debugging, and diagnosis. Choose per task; writing a file alone does
  not require Sonnet.
- Never use `WebSearch` or `WebFetch` in the main thread. Route external research
  through `explorer`.
- Skill discovery is manual and on demand. Do not run a catalogue before a task
  or reject work because matching was not performed. Pass each applicable
  skill's exact name and resolved context to the worker.
- Workers invoke every skill named in their prompt, treat supplied skill context
  as resolved, and stop if a named skill or required context is unavailable.

## Bounds

- Dispatch 1 worker per independent unit with disjoint writes and run those
  units concurrently. Run dependent work serially; never let 2 agents edit the
  same file.
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
- Workers gather with `ctx_batch_execute`, follow up with one batched
  `ctx_search`, and process with `ctx_execute`/`ctx_execute_file`
  (`intent` filtered). Never return full files, logs, SQL, result
  sets, or build output; keep raw output in the sandbox.
- Code-oriented agents use CodeGraph first, then Context Mode, then LSP and the `coding` skill. The orchestrator owns all
  human-facing prose, which follows `Straight_to_the_Point`.
