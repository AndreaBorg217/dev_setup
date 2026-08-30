# Merge-request workflow

## Gather evidence

Before drafting:

1. Resolve the source and target branches; do not assume either name.
2. Check for an existing MR from the source branch.
3. Review the commit range, three-dot diff, changed-file list, and actual validation results.
4. Identify deployment order, CI/CD jobs, environment progression, dependent or prerequisite MRs, runtime success signals, and rollback limitations.
5. Check `.gitlab/merge_request_templates/` for a repository-required template.

Repository templates take precedence. Ensure they still address the five personal content areas, even if their headings differ. If no repository template applies, render [../assets/merge-request-template.md](../assets/merge-request-template.md) with all placeholders and instructional comments replaced.

GitLab project templates are Markdown files under `.gitlab/merge_request_templates/` and must exist on the default branch to appear in GitLab. The installed CLI can select a local repository template with `glab mr create --template NAME`.

## Required content

### Summary

Explain what changed and why. Describe the problem or ticket context, the intended outcome, and the material implementation choices. Do not merely list files.

### Testing

List exact automated and manual checks with observed results. Mark only checks that actually ran. State failures, skipped checks, and pending runtime or environment QA explicitly.

### Deployment

Explain how the change reaches each environment and in what order. Reference relevant CI/CD jobs or pipelines, prerequisite and follow-up MRs, migrations, feature flags, manual steps, dashboards, logs, queries, or other observable success criteria.

### Rollback

Give executable reversal or recovery steps in order. Include limitations such as irreversible writes, schema incompatibility, data loss, downtime, offset changes, or a bounded rollback window. Do not write only “revert the MR” when operational state also changes.

### Considerations

Cover performance and operational impact, security or compatibility concerns, known technical debt, reviewer focus, and follow-up work. Write `None identified` only after considering each area.

## Title and metadata

- Use `TICKET: concise imperative summary` when a ticket key exists.
- Specify source and target branches explicitly.
- Self-assign using the authenticated username for the active host.
- Normally request source-branch removal after merge.
- Use `-R GROUP/PROJECT` for cross-project creation.
- Do not create a duplicate MR for the same source branch.

## QA and creation

Present the title and fully rendered description to the user. Obtain explicit approval immediately before `glab mr create`; prior approval to commit or push does not authorize MR creation.

After creation, return the MR URL and report source/target branches, pipeline state if available, and any pending deployment or testing item. Do not merge, close, comment, resolve discussions, or mutate CI unless separately approved.
