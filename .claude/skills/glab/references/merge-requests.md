# Merge-request workflow

## Gather evidence

Before drafting:

1. Resolve the source and target branches; do not assume either name.
2. Check for an existing MR from the source branch.
3. Review the commit range, three-dot diff, changed-file list, and actual validation results.
4. Identify deployment order, CI/CD jobs, environment progression, dependent or prerequisite MRs, runtime success signals, and rollback limitations.
5. Check `.gitlab/merge_request_templates/` for a repository-required template.

Use the validation budget once, at the final pre-MR state:

- Reuse recorded targeted and full-suite results when runtime-relevant source
  has not changed. Do not rerun them because README, comments, formatting-only
  Python, or docstrings changed.
- If a full suite is appropriate and has not run, request approval and run it
  once immediately before final MR QA. Do not run it during each implementation
  iteration.
- If the plan assigns exhaustive verification to CI, do not run it locally;
  state it as pending CI in `Testing`.
- If runtime-relevant source changed after a full run, ask the user before one
  exceptional rerun. Never spend that rerun automatically.

Repository templates take precedence. Ensure they still address the five personal content areas, even if their headings differ. If no repository template applies, render [../assets/merge-request-template.md](../assets/merge-request-template.md) with all placeholders and instructional comments replaced.

GitLab project templates are Markdown files under `.gitlab/merge_request_templates/` and must exist on the default branch to appear in GitLab. The installed CLI can select a local repository template with `glab mr create --template NAME`.

## Required content

### Summary

Explain what changed and why. Describe the problem or ticket context, the intended outcome, and the material implementation choices. Do not merely list files.

### Testing

List exact automated and manual checks with observed results. Mark only checks that actually ran. State failures, skipped checks, and pending runtime or environment QA explicitly.

### Deployment

Explain how the change reaches each environment and in what order. Reference relevant CI/CD jobs or pipelines, prerequisite and follow-up MRs, migrations, feature flags, manual steps, dashboards, logs, queries, or other observable success criteria.

Always configure native **Merge request dependencies** and document the merge order:

- In each dependent MR, link every prerequisite by its full MR URL and explicitly state `Merge <prerequisite MR> before this MR`. For a chain, show the ordered MR links.
- Add reciprocal links to follow-up MRs in prerequisite descriptions when those MRs exist and the updates are authorized. If an MR has not been created yet, mark its link as pending and add the real URL once available; never invent an IID or URL.
- Configure each prerequisite as a native Merge request dependency, within the authorized mutation scope. Follow [glab-cli.md → Merge request dependencies](glab-cli.md#merge-request-dependencies) to create it directly with `glab api`, then verify the saved relationship. Do not post a note or open a discussion for dependency setup. Description links alone do not fulfill this requirement. If unavailable, keep the explicit links and order in the descriptions and report the limitation and pending setup.
- Before merging a dependent MR, verify that every prerequisite is merged. Description links alone do not enforce merge order.
- For a chain of branch-per-step MRs, follow [glab-cli.md → Stacked merge requests](glab-cli.md#stacked-merge-requests) for targets, merge order and retargeting.

### Rollback

Give executable reversal or recovery steps in order. Include limitations such as irreversible writes, schema incompatibility, data loss, downtime, offset changes, or a bounded rollback window. Do not write only “revert the MR” when operational state also changes.

### Considerations

Cover performance and operational impact, security or compatibility concerns, known technical debt, reviewer focus, and follow-up work. Write `None identified` only after considering each area.

## Title and metadata

- Use `TICKET: concise imperative summary` when a ticket key exists.
- Specify source and target branches explicitly.
- Always assign the MR. Self-assign using the authenticated username for the active host, read from the CLI. If it cannot be inferred, ask with `AskUserQuestion` before creating the MR.
- Normally request source-branch removal after merge.
- Use `-R GROUP/PROJECT` for cross-project creation.
- Do not create a duplicate MR for the same source branch.

## QA and creation

Present the title, fully rendered description, and proposed native dependency relationships for QA. Include dependency setup in the requested mutation scope. Obtain explicit approval immediately before `glab mr create`; prior approval to commit or push does not authorize MR creation.

Once both MR URLs exist, configure the approved native dependencies and verify them before reporting dependency setup complete. Reuse existing relationships; report failed or pending setup explicitly. Return the MR URL and report source/target branches, verified dependencies, pipeline state if available, and any pending deployment or testing item. Do not merge, close, post unrelated comments, resolve discussions, or mutate CI unless separately approved.
