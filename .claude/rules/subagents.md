# Subagents

- Use subagents for bounded delegated work, noisy commands, research, or context buffering. Keep the main conversation as the driver and orchestrator.
- Pick a specific `subagent_type` instead of defaulting to `general-purpose`:
  `Explore` or `caveman:cavecrew-investigator` for locating code,
  `caveman:cavecrew-builder` for a bounded 1-2 file edit,
  `caveman:cavecrew-reviewer` for diff/PR review, and `Plan` for design work.
  Fall back to `general-purpose` only when none of those fit.
- Batch related lookups into one dispatch instead of firing several tiny subagents.
- If a dispatch would just repeat a question an earlier agent in this same
  session already investigated, answer it from that agent's returned findings,
  or re-dispatch with a narrower prompt referencing what's already known -
  never re-ask the same open-ended question from scratch.
- Set the Agent `model` parameter explicitly; `model` and `subagent_type` are separate. Route planning and production-incident orchestration to `opus`, implementation/review/ambiguous work to `sonnet`, and mechanical or verbose work to `haiku`.
- Use the main thread for one small lookup or command whose output should stay
  under roughly 1-2k tokens. Delegate noisy output, multiple files, web/log
  research, dependency/test/build/check output, and parallelizable work.
- Never call `WebSearch` or `WebFetch` from the main thread. Delegate web research, URLs, and documentation retrieval to a Haiku subagent and return only the requested sourced answer.
- Prefer `caveman` agents (installed plugin) with compressed output when they
  fit the task.
- Ask subagents that run noisy commands or fetch docs to retain raw output in
  their context and return only status, exact command/query, relevant snippets,
  source links, and the recommended next action.

## Leaf tier

Subagents must not call `Agent`. This is enforced by `scripts/no-nested-agents.py` and the `general-purpose` agent override. If a subagent discovers that work needs splitting, it must finish what it reasonably can and return the proposed split to the main thread. The main thread owns fanout and uses the `Workflow` tool for larger pipelines.

## Parallelism judgement

Classify before dispatching more than one subagent:

- **Independent -> parallel.** Separate repos/projects, separate files with
  no shared symbol, separate tenants/jurisdictions, read-only
  investigations, same-tier environments. One message, multiple `Agent`
  calls (e.g. `caveman:cavecrew-builder` for independent file edits, each
  returning only the required diff result).
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

Decision test: uncertainty about the fix means the work is not parallel-safe yet. Parallelise only known-shape work; probe first to turn unknown shape into known shape.

Anti-patterns: N agents independently rediscovering the same fix; fanning
out before any consumer has been proven; parallel agents writing the same
file; stg and prod in the same batch (always sequential).

Cost note: one probe is cheaper than N-1 failed fanouts plus retries.
