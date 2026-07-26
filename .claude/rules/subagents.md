# Subagents

- Use subagents for bounded delegated work, noisy commands, research, or
  context buffering. Keep the main conversation as the driver/orchestrator.
- Batch related lookups into one dispatch instead of firing several tiny
  subagents; each subagent starts with a cold, independent cache.
- Set the Agent `model` parameter explicitly. The routing hook deterministically
  rewrites missing or mismatched models without another model turn;
  `CLAUDE_CODE_SUBAGENT_MODEL` stays at `inherit` so the hook remains the
  single source of truth instead of being silently overridden. The only
  supported subagent model families are `opus`, `sonnet`, and `haiku`.
  `fable` and `best` are disabled and rewritten.
    - `opus`: planning (`Plan` agent) and production-incident orchestration.
    - `sonnet`: the default - implementation, review, and anything ambiguous.
    - `haiku`: pure mechanical execution and summarization of verbose output -
      Explore/locate, log search, web search, docs/URL fetch, tests, builds,
      dependency installs, checks, curl/API probes. The moment a task also needs
      debugging, triage, investigation, review, or planning, it escalates to
      `sonnet` - the hook enforces this from the request text, not the tool
      name alone.
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
