# Subagents

- Use subagents for bounded delegated work, noisy commands, research, or
  context buffering. Keep the main conversation as the driver/orchestrator.
  Subagents are leaf-tier: they must not call the `Agent` tool themselves. This
  is enforced, not just advised - a `PreToolUse` hook
  (`scripts/no-nested-agents.py`) denies any `Agent` call whose stdin carries
  an `agent_id` (i.e. it originated inside a subagent), and the project-level
  `.claude/agents/general-purpose.md` override strips the `Agent` tool from
  `general-purpose` entirely, since that is the built-in type most likely to
  be dispatched by default and the only one with every tool.
- Pick a specific `subagent_type` instead of defaulting to `general-purpose`:
  `Explore` or `cavecrew-investigator` for locating code, `cavecrew-builder`
  for a bounded 1-2 file edit, `cavecrew-reviewer` for diff/PR review, `Plan`
  for design work. Fall back to `general-purpose` only when none of those fit.
- Batch related lookups into one dispatch instead of firing several tiny
  subagents.
- If a dispatch would just repeat a question an earlier agent in this same
  session already investigated, answer it from that agent's returned summary,
  or re-dispatch with a narrower prompt referencing what's already known -
  never re-ask the same open-ended question from scratch.
- Set the Agent `model` parameter explicitly. `haiku`/`sonnet`/`opus` are
  values for `model`, never for `subagent_type`. The only supported subagent model families
  are `opus`, `sonnet`, and `haiku`. Model tiers (all set via `model`, `subagent_type` picks the
  agent separately):
    - `opus`: planning (`Plan` agent) and production-incident orchestration.
    - `sonnet`: the default - implementation, review, and anything ambiguous.
    - `haiku`: pure mechanical execution and summarization of verbose output -
      Explore/locate, log search, web search, docs/URL fetch, tests, builds,
      dependency installs, checks, curl/API probes, loops, polling.
- Use the main thread for one small lookup or command whose output should stay
  under roughly 1-2k tokens. Delegate noisy output, multiple files, web/log
  research, dependency/test/build/check output, and parallelizable work.
- Prefer `caveman` agents (installed plugin) with compressed output when they
  fit the task.
- Ask subagents that run noisy commands or fetch docs to retain raw output in
  their context and return only status, exact command/query, relevant snippets,
  source links, and the recommended next action.

## Parallelism judgement

Classify before dispatching more than one subagent:

- **Independent -> parallel.** Separate repos/projects, separate files with
  no shared symbol, separate tenants/jurisdictions, read-only
  investigations, same-tier environments. One message, multiple `Agent`
  calls (e.g. cavecrew-builder for independent file edits, each returning
  only a diff summary).
- **Sequential -> serial.** B needs an artifact, decision, or exact diff
  that only exists after A runs. Also: two agents that would edit the same
  file - collapse into one agent instead.
- **Probe-then-fanout -> one shared change, N consumers.** Never fan out to
  all N in parallel off a shared-unit change. Order:
  1. One subagent changes the shared unit (library, schema, API contract).
  2. One subagent applies + verifies it against exactly ONE consumer and
     returns the concrete adaptation - exact diff, commands, config keys,
     version pins - not just pass/fail.
  3. Orchestrator fans out the remaining N-1 consumers in parallel, pasting
     the probe's adaptation verbatim into every dispatch prompt.

Decision test: uncertainty about the fix means the work is not
parallel-safe yet. Parallelise only known-shape work; probe first to turn
unknown shape into known shape.

Anti-patterns: N agents independently rediscovering the same fix; fanning
out before any consumer has been proven; parallel agents writing the same
file; stg and prod in the same batch (always sequential).

Cost note: one probe is cheaper than N-1 failed fanouts plus retries.

## Fan-out belongs to the main thread

A subagent must not dispatch further subagents (enforced, see above). If a
subagent discovers mid-task that the remaining work needs splitting, it stops
and returns the proposed split - what to split, how, and why - instead of
attempting it. The main thread fans out from there; for more than a handful of
parallel workers or a multi-stage pipeline, use the `Workflow` tool rather than
hand-rolled batches of `Agent` calls.
