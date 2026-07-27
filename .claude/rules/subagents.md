# Subagents

- Use subagents for bounded delegated work, noisy commands, research, or
  context buffering. Keep the main conversation as the driver/orchestrator.
  Subagents are leaf-tier: they must not call the `Agent` tool themselves.
- Batch related lookups into one dispatch instead of firing several tiny
  subagents.
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
- For independent file edits (no cross-file dependencies), dispatch
  cavecrew-builder agents in parallel - each returns only a diff summary
  to the main thread. Keep edits in the main thread only when one change
  depends on the output of another.
- Ask subagents that run noisy commands or fetch docs to retain raw output in
  their context and return only status, exact command/query, relevant snippets,
  source links, and the recommended next action.
