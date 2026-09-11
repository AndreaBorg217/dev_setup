# CLAUDE.md

All files under `rules/` are binding, not advisory, for every task in every repo.

The configured `Straight_to_the_Point` style applies to every human-facing
response and artifact, including skill and subagent output. Skill templates set
required content; write it in the configured style.

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

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it before grep/find or reading files when you need to understand or locate code:

- MCP tool (when available): `codegraph_explore` returns relevant symbols' line-numbered source, call paths, and blast radius. If it is deferred, load it by name through tool search.
- Shell fallback: `codegraph explore "<symbol names or question>"` returns the same context for subagents and non-MCP sessions.
- Before selecting targeted tests, pass the changed source paths to
  `codegraph affected --stdin --quiet`; include relevant untracked paths
  explicitly and keep any repository-required full-suite checks.

If there is no `.codegraph/` directory, skip CodeGraph; initializing a project index is the user's decision.
<!-- CODEGRAPH_END -->
