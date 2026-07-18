# Subagents

- Use subagents for bounded delegated work, noisy commands, research, or
  context buffering. Keep the main conversation as the driver/orchestrator.
- Batch related lookups into one dispatch instead of firing several tiny
  subagents; each subagent starts with a cold, independent cache.
- Set the Agent `model` parameter explicitly. The routing hook checks the
  detailed defaults: `haiku` for search/read/noisy/research/triage/loops,
  and `sonnet` for planning, implementation, or edits. Opus requires explicit
  user permission for each Agent call; if declined, retry with Sonnet.
- Prefer caveman agents with compressed output when they fit the task. For
  multi-file implementation, keep coherence in the main thread.
- Ask subagents that run noisy commands or fetch docs to retain raw output in
  their context and return only status, exact command/query, relevant snippets,
  source links, and the recommended next action.
