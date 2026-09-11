# CLAUDE.md

All files under `rules/` are binding for every task in every repository.

# Compact instructions

When compacting, preserve: task goals, decisions made, file changes in progress, test results, error messages under investigation.
Discard: exploratory search results, raw command output, intermediate reasoning, completed subtask details.

Preserve these binding rules during compaction:

@rules/safety.md
@rules/coding.md
@rules/workflow.md
@rules/subagents.md
@rules/interaction.md
@rules/config-management.md

<!-- CODEGRAPH_START -->
## CodeGraph

When `.codegraph/` exists, use `codegraph_explore` before text search or file
reads for structural source questions. Non-MCP sessions use `codegraph explore`.
Use `codegraph affected --stdin --quiet` to select targeted-test candidates.
Do not initialize CodeGraph without the user's approval.
<!-- CODEGRAPH_END -->
