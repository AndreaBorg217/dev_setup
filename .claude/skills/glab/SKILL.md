---
name: glab
description: Manages GitLab via glab - MRs, issues, pipelines and API calls. Use when working with GitLab MRs, pipelines or discussions.
when_to_use: "glab, glab mr, glab ci, GitLab API, REST, GraphQL, MR IID, source branch, target branch, pipeline, discussion, comment, reply, resolve discussion, reopen discussion, merge request description, MR template, merge, close MR, CI mutation, authenticated account, host, project"
---

# GitLab with glab

Load this skill once before the first `glab` or GitLab API command in a task. Keep its instructions active for the rest of that task.

## Use the references

- Before any `glab` or GitLab API command, read the relevant section of [references/glab-cli.md](references/glab-cli.md). It contains copy-ready authentication, MR, REST, GraphQL, comment, discussion, and CI commands.
- To locate an unknown repository by its contents, use [group code search and file reads](references/glab-cli.md#find-a-repository-by-its-contents).
- Before drafting, creating, or updating an MR description, read [references/merge-requests.md](references/merge-requests.md) and render [assets/merge-request-template.md](assets/merge-request-template.md).
- If the task needs a `git` command, load the separate `git` skill before running it.

## Establish the GitLab target

Resolve the active host, project, authenticated account, MR IID, source branch, target branch, and pipeline or discussion identifiers from command output. Never guess or hardcode them.

Prefer high-level `glab mr` and `glab ci` commands. Use REST when a high-level command cannot express the operation. Use GraphQL only for fields unavailable through those routes.

Keep output targeted. Prefer structured JSON and narrow projections. Never expose tokens, credential files, secret-bearing configuration, or unfiltered output that may contain them.

## Approval

Skill invocation does not authorize a mutation. Read-only inspection may run when relevant. Obtain explicit QA and approval immediately before authentication changes, MR creation or updates, comments, replies, discussion resolution or reopening, merges, closes, CI mutations, and other GitLab mutations.

## MR assignee and merge options

Every MR must have an assignee. Infer the user from the CLI (`glab auth status` or `glab api user` on the active host) and pass `--assignee` on `glab mr create`. If the user cannot be inferred, use `AskUserQuestion`; never create an MR unassigned.

Every MR must squash commits and delete the source branch on merge. Pass `--squash-before-merge --remove-source-branch` on `glab mr create`. On an existing MR, read `squash` and `force_remove_source_branch` first: `glab mr update` only toggles these flags, so pass a flag only when its current value is false.

## MR descriptions

Every final MR description must contain task-specific `Summary`, `Testing`, `Deployment`, `Rollback`, and `Considerations` content. State what actually ran and mark pending checks plainly. Use a mandatory repository template when present; otherwise use the bundled template.

Always use GitLab's native **Merge request dependencies** for dependent MRs to enforce merge order. Create each relationship directly with `glab api` using the dependency endpoint, then verify the saved dependency. Do not post a note or open a discussion to block an MR. Follow [the dependency commands](references/glab-cli.md#merge-request-dependencies). Also link every prerequisite and state the merge order in `Deployment`. Description links alone do not fulfill this requirement. If the feature is unavailable, report the limitation and pending dependency setup explicitly. Verify prerequisites are merged before merging a dependent MR.

Reserve any approved full local build/test suite for the final pre-MR state and
run it at most once per session, repository, and runner. Reuse that result after
prose-only changes; leave exhaustive verification pending CI when the plan
assigns it to CI. Follow the validation-budget rules in
`references/merge-requests.md`.

Present the final title and rendered description for QA before creating or updating the MR.
