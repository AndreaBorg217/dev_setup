# CLAUDE.md

## Dispatch gate (binding)

Keep the main context light. Before repository, data, or external-source work,
choose the least expensive capable path:

- Use Context Mode directly for a bounded extraction that returns the needed
  answer without substantive side-task reasoning.
- Use Haiku `explorer` for noisy factual collection and external research.
- Use Sonnet `analyst` for bounded comparison, critique, diagnosis, or sparring.
- Use Sonnet `builder` for implementation and implementation-related diagnosis.
- Use Haiku `artifact-writer` only for fully specified mechanical artifacts.

The main thread owns user dialogue, decomposition, decisions, coordination, and
final synthesis. Every worker call must set `subagent_type` and `model`; choose
Haiku or Sonnet explicitly. An Opus worker requires explicit user approval.

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
