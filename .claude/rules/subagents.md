# Subagents

Delegate automatically when the work fits; the user need not ask. The main
thread is a thin orchestrator: fan out, then fan in receipts only.

Before answering each user turn or loading new substantive context, decide
whether the work belongs to an existing owner or can be delegated as a bounded
task. Delegate first; do not load the same context in the main thread and only
then send it to a worker. Keep coordination, synthesis, user dialogue, and
judgement over returned evidence in the main thread.

## When to delegate

- The work has an explicit objective, scope, and acceptance check.
- Collection is noisy or menial and the main thread needs only derived facts,
  not raw output (review comments, logs, multi-file scans).
- The work splits into independent units with disjoint file ownership (per
  repository, file, or MR). Run those concurrently; serial execution that bloats
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
- Skill discovery is manual and on demand — planner's one bounded inventory at plan time is the only exception. Do not run a catalogue before a task
  or reject work because matching was not performed. Pass each applicable
  skill's exact name and resolved context to the worker.
- Workers invoke every skill named in their prompt, treat supplied skill context
  as resolved, and stop if a named skill or required context is unavailable.

## Bounds

- Assign each file to 1 owning worker for the duration of the investigation or
  change. No other worker or the main thread rereads or edits that file. Route
  later questions about it back to the same owner.
- Batch every currently known question about a file into its owner's initial
  prompt. Ten questions about one file go to one worker, not ten consecutive
  workers. Continue the owner when new questions arise instead of spawning a
  fresh worker with the same context.
- Every agent is a leaf. Do not use nested, verifier, recovery, or blind
  replacement agents. Reassign ownership only when the owner is unavailable or
  demonstrably failed, and include its existing evidence in the handoff.
- Give a read-only worker 1 owned file or independent evidence source, all
  related questions, a stop condition, and a 1,500-character receipt limit.
  Keep raw output in its context.
- Make implementation prompts self-contained: objective, permitted writes,
  resolved decisions, constraints, acceptance criteria, applicable Skills and
  context, and at most 1 approved targeted check.
- Maintain the file-to-worker ownership map across follow-up turns. Batch
  related lookups. Do not repeat an owner's searches, redispatch the same open
  question, or reread unchanged evidence in the main thread.

## Tool and output discipline

- Set both `subagent_type` and `model` explicitly. Never dispatch Opus as a
  worker.
- Workers gather with `ctx_batch_execute`, follow up with one batched
  `ctx_search`, and process with `ctx_execute`/`ctx_execute_file`
  (`intent` filtered). Never return full files, logs, SQL, result
  sets, or build output; keep raw output in the sandbox.
- Code-oriented agents use CodeGraph first, then Context Mode, then LSP and the `coding` skill. The orchestrator owns all
  human-facing prose, which follows `Straight_to_the_Point`.
