# CLAUDE.md

All files under `rules/` are binding, not advisory, for every task in every repo.

The `Straight_to_the_Point` output style is binding for every piece of human-facing prose I produce, in every context: chat replies, MR/PR descriptions and comments, commit messages, Jira/Notion content, docs, and any subagent or skill output rendered to a reader. A skill's own template or instructions (headings, "cover X", "explain Y") describe required *content*, not permission to write it in bureaucratic, padded, or AI-generic prose. Fill every mandated section in plain, direct sentences per that style. This is not optional and does not reset between skills or subagents.

# Compact instructions

When compacting, preserve: task goals, decisions made, file changes in progress, test results, error messages under investigation.
Discard: exploratory search results, raw command output, intermediate reasoning, completed subtask details.

These are my rules, adherence to them is not optional, they must be adhered to at all points, and during compaction you must ensure they remain in context:

@rules/safety.md
@rules/coding.md
@rules/workflow.md
@rules/subagents.md
@rules/interaction.md
@rules/config-management.md
@RTK.md
