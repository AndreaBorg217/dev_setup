---
name: glab
description: Use when any GitLab operation is requested, including read-only inspection (glab status, MR/issue view, pipeline status, API GET) and mutations (create/update/merge/close MR, post comments/discussions, trigger/retry/cancel CI pipelines, manage labels/approvals).
---

# GitLab with glab

Load this skill once before the first `glab` or GitLab API command in a task. Keep its instructions active for the rest of that task.

## Use the references

- Before any `glab` or GitLab API command, read the relevant section of [references/glab-cli.md](references/glab-cli.md). It contains copy-ready authentication, MR, REST, GraphQL, comment, discussion, and CI commands.
- Before drafting, creating, or updating an MR description, read [references/merge-requests.md](references/merge-requests.md) and render [assets/merge-request-template.md](assets/merge-request-template.md).
- If the task needs a `git` command, load the separate `git` skill before running it.

## Establish the GitLab target

Resolve the active host, project, authenticated account, MR IID, source branch, target branch, and pipeline or discussion identifiers from command output. Never guess or hardcode them.

Prefer high-level `glab mr` and `glab ci` commands. Use REST when a high-level command cannot express the operation. Use GraphQL only for fields unavailable through those routes.

Keep output targeted. Prefer structured JSON and narrow projections. Never expose tokens, credential files, secret-bearing configuration, or unfiltered output that may contain them.

## Approval

Skill invocation does not authorize a mutation. Read-only inspection may run when relevant. Obtain explicit QA and approval immediately before authentication changes, MR creation or updates, comments, replies, discussion resolution or reopening, merges, closes, CI mutations, and other GitLab mutations.

## MR descriptions

Every final MR description must contain task-specific `Summary`, `Testing`, `Deployment`, `Rollback`, and `Considerations` content. State what actually ran and mark pending checks plainly. Use a mandatory repository template when present; otherwise use the bundled template.

Write every section, comment, and reply in `Straight_to_the_Point` voice: plain sentences, no filler, no legalese, no padding a section out to look thorough. The template's headings are required content, not licence to write bureaucratic prose.

Present the final title and rendered description for QA before creating or updating the MR.
