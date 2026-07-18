# Subagents

- Use subagents for bounded delegated work, noisy commands, research, or
  context buffering. Keep the main conversation as the driver/orchestrator.
- Batch related lookups into one dispatch instead of firing several tiny
  subagents; each subagent starts with a cold, independent cache.
- Set the Agent `model` parameter explicitly. The routing hook deterministically
  rewrites missing or mismatched models without another model turn: `haiku` for
  search/read/noisy/research/triage/loops, and `sonnet` for planning,
  implementation, or edits. It also replaces confidently mismatched generic
  agents with the matching cavecrew or Plan agent. Opus is preserved but
  requires explicit user permission for each Agent call.
- Prefer caveman agents with compressed output when they fit the task.
- For independent file edits (no cross-file dependencies), dispatch
  cavecrew-builder agents in parallel — each returns only a diff summary
  to the main thread. Keep edits in the main thread only when one change
  depends on the output of another.
- Ask subagents that run noisy commands or fetch docs to retain raw output in
  their context and return only status, exact command/query, relevant snippets,
  source links, and the recommended next action.
