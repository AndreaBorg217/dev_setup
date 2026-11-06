# glab CLI reference

Replace the generic values in one block, then run that block unchanged. Mutations require explicit approval immediately before execution.

## Install

```bash
brew install glab
```

## Authentication

Resolve the configured host, verify stored authentication, then make a live API call so an expired or unauthorized token cannot pass unnoticed:

```bash
GLAB_HOST="$(glab config get gitlab_host)"
glab --version
glab auth status --hostname "$GLAB_HOST"
glab api --hostname "$GLAB_HOST" user >/dev/null
```

If either auth check fails, stop. With approval, start the interactive login and verify again:

```bash
GLAB_HOST="$(glab config get gitlab_host)"
glab auth login --hostname "$GLAB_HOST"
glab auth status --hostname "$GLAB_HOST"
glab api --hostname "$GLAB_HOST" user >/dev/null
```

Discussion writes need a token with API access. Never put a token in a command, print it, read it from glab configuration, or ask for it in chat.

## Find a repository by its contents

When the owning repository is unknown, search a distinctive resource name or
configuration key across the supplied group before cloning candidate projects.
Reuse the verified host from Authentication; URL-encode nested group paths.

```bash
GLAB_GROUP_PATH="example/platform"
GLAB_SEARCH="distinctive-resource-name"
GLAB_GROUP_ENCODED=$(jq -nr --arg path "$GLAB_GROUP_PATH" '$path | @uri')
glab api --hostname "$GLAB_HOST" -X GET \
  "groups/$GLAB_GROUP_ENCODED/search" \
  -f scope=blobs -f "search=$GLAB_SEARCH" -f per_page=30 -f page=1 \
  | jq '[.[] | {project_id, path, ref, startline}]'
```

Search results are leads, not the full configuration. Read the matching file
using its returned project ID, path, and ref; do not assume the default branch.

```bash
GLAB_PROJECT_ID="returned-project-id"
GLAB_FILE_PATH="path/from/search.yaml"
GLAB_REF="returned-ref"
GLAB_FILE_ENCODED=$(jq -nr --arg path "$GLAB_FILE_PATH" '$path | @uri')
glab api --hostname "$GLAB_HOST" -X GET \
  "projects/$GLAB_PROJECT_ID/repository/files/$GLAB_FILE_ENCODED/raw" \
  -f "ref=$GLAB_REF" | sed -n '1,160p'
```

If results fill the page, request the next page as needed. Empty results do not
prove absence: access, indexing, branch coverage, and GitLab search availability
can limit results. If group blob search is unavailable, enumerate accessible
projects (including subgroups). Set `GLAB_PROJECT_ID` and `GLAB_REF` from a
selected project's `id` and `default_branch`, then inspect its tree:

```bash
glab api --hostname "$GLAB_HOST" --paginate \
  "groups/$GLAB_GROUP_ENCODED/projects?include_subgroups=true&per_page=100" \
  | jq -c '.[] | {id, path_with_namespace, default_branch}'
glab api --hostname "$GLAB_HOST" --paginate -X GET \
  "projects/$GLAB_PROJECT_ID/repository/tree" \
  -f "ref=$GLAB_REF" -f recursive=true -f per_page=100 \
  | jq -r '.[] | select(.type == "blob") | .path' | head -n 100
```

Filter tree paths for the relevant component before reading files. Keep raw-file
reads bounded and avoid secret-bearing paths. Repository manifests describe
intended configuration; verify live state separately when that distinction matters.

## Merge requests

Find an MR by source branch before creating another one:

```bash
GLAB_PROJECT="group/project"
GLAB_SOURCE_BRANCH="feature-branch"
glab mr list \
  -R "$GLAB_PROJECT" \
  --source-branch "$GLAB_SOURCE_BRANCH" \
  --output json \
  | jq -c '.[] | {iid, title, source_branch}' | head -n 30
```

Find MRs by author or search text:

```bash
GLAB_PROJECT="group/project"
GLAB_AUTHOR="username"
glab mr list -R "$GLAB_PROJECT" --author "$GLAB_AUTHOR" --all | head -n 30
```

Search open, closed, and merged MRs by ticket or other text. `--all` includes
merged work; `--per-page 30` limits each page. Use `--page 2` and subsequent pages
when more matches are needed.

```bash
GLAB_PROJECT="group/project"
GLAB_SEARCH="search text"
glab mr list -R "$GLAB_PROJECT" --all --search "$GLAB_SEARCH" --output json --per-page 30 \
  | jq '[.[] | {iid, title, state, merged_at, source_branch, target_branch, web_url}]'
```

Inspect metadata, comments, structured fields, and the diff. Keep every read
capped (the hook denies raw `mr view --comments`, `mr diff`, and `api` output):

```bash
GLAB_PROJECT="group/project"
GLAB_MR_IID="123"
glab mr view "$GLAB_MR_IID" -R "$GLAB_PROJECT" --comments | head -n 100
glab mr view "$GLAB_MR_IID" -R "$GLAB_PROJECT" --output json \
  | jq '{title, state, source_branch, target_branch, web_url}'
glab mr diff "$GLAB_MR_IID" -R "$GLAB_PROJECT" | head -n 100
```

## Merge request dependencies

Create native **Merge request dependencies** directly with `glab api`; do not post a note or open a discussion to set blocking relationships. See the [create dependency API](https://docs.gitlab.com/api/merge_requests/#create-a-merge-request-dependency) and [dependency behavior](https://docs.gitlab.com/user/project/merge_requests/dependencies/).

Resolve the host and both MRs from metadata. The endpoint identifies the **dependent** MR by owning project ID and project-local `.iid`; `blocking_merge_request_id` is the prerequisite's global `.id`, not its IID. This supports same-project and cross-project dependencies.

Read existing blockers first and reuse a matching relationship:

```bash
GLAB_HOST="gitlab.example.com"
GLAB_DEPENDENT_PROJECT_ID="12345"
GLAB_DEPENDENT_MR_IID="123"
glab api --hostname "$GLAB_HOST" \
  "projects/$GLAB_DEPENDENT_PROJECT_ID/merge_requests/$GLAB_DEPENDENT_MR_IID/blocks" \
  | jq '[.[] | {block_id: .id, blocker: (.blocking_merge_request | if . == null then null else {id, iid, project_id, state, web_url} end)}]'
```

After approval, add the prerequisite directly:

```bash
GLAB_BLOCKING_MR_ID="987654"
glab api --hostname "$GLAB_HOST" -X POST \
  "projects/$GLAB_DEPENDENT_PROJECT_ID/merge_requests/$GLAB_DEPENDENT_MR_IID/blocks" \
  -F "blocking_merge_request_id=$GLAB_BLOCKING_MR_ID" \
  | jq '{block_id: .id, blocker: (.blocking_merge_request | {id, iid, project_id, state, web_url})}'
```

Re-run the blockers read to verify the saved relationship. On a 409, verify the existing relationship instead of retrying blindly. Investigate permission or availability failures and report pending setup explicitly. Do not fall back to posting quick-action comments.

The dependent project requires Premium or Ultimate. Closed prerequisites still block; verify all prerequisites are merged before merging a dependent MR. A missing blocker object indicates restricted visibility, not a satisfied dependency. Avoid cycles. For A → B → C, add A as B's blocker and B as C's blocker. Keep full MR links and merge order in descriptions; deployment readiness remains a separate check.

### Stacked merge requests

Stack when a change must reach production in ordered, separately observable steps, so each step is merged, deployed and checked before the next one starts. The typical case is a rollout that must not disrupt service, such as moving a workload over one pod at a time (a chain of MRs where each step shifts one more pod and the previous step has to be healthy first). Do not stack independent changes, or changes that are safe to ship together: use one MR, or separate MRs against the default branch. Use one branch and one MR per step.

- Build: branch each step from the previous branch, one commit per logical unit. Create each MR with `--target-branch` set to the previous branch; the first targets the default branch. Create and update MRs only after approval, per step.
- Link: set each MR as a native dependency of the next (see above). In every description, list the chain as a numbered list of MR links in merge order, state the MR's own step, and add `Merge <previous MR> before this MR`. Update earlier descriptions when the chain changes, after approval.
- Merge: strictly in order, one at a time. Before each merge, check the pipeline is green and any soak or observation check named in the description has passed.
- Retarget: observed behaviour, not a documented guarantee: when a parent merges with its source branch deleted (`glab mr merge "$GLAB_MR_IID" --remove-source-branch`, after approval), GitLab moved the child's target branch to the default branch itself. The retargeted child did not get a new pipeline. Start one with `glab ci run --branch "$GLAB_CHILD_BRANCH"`, or add `--mr` if the repository uses merge request pipelines (or press Run pipeline). After each parent merges, check the child's `target_branch`, mergeability and pipeline before merging it. Fallback only: if the target still points at the merged parent branch, run `glab mr update "$GLAB_MR_IID" --target-branch "$GLAB_DEFAULT_BRANCH"`. If the child's base changed, rebase it onto the default branch and push with `--force-with-lease`, following the `git` skill and its approval rules.
- Roll back: revert the offending MR, then rebase or retarget the later MRs.
- `glab stack` (experimental, one MR per commit) does not match this branch-per-MR flow and does not set native dependencies. Use `mr create`, `mr update` and the dependency API above.

## Comments and discussions

Use the high-level commands when the installed glab version supports them.

List unresolved discussions:

```bash
GLAB_PROJECT="group/project"
GLAB_MR_IID="123"
glab mr note list "$GLAB_MR_IID" \
  -R "$GLAB_PROJECT" \
  --state unresolved \
  --output json
```

Create a comment or reply to a discussion:

```bash
GLAB_PROJECT="group/project"
GLAB_MR_IID="123"
GLAB_MESSAGE="Comment with the relevant result."
glab mr note create "$GLAB_MR_IID" -R "$GLAB_PROJECT" --message "$GLAB_MESSAGE"
```

```bash
GLAB_PROJECT="group/project"
GLAB_MR_IID="123"
GLAB_DISCUSSION_ID="discussion-id"
GLAB_REPLY="Reply with the change and its verification."
glab mr note create "$GLAB_MR_IID" \
  -R "$GLAB_PROJECT" \
  --reply "$GLAB_DISCUSSION_ID" \
  --message "$GLAB_REPLY"
```

Resolve or reopen a discussion:

```bash
GLAB_PROJECT="group/project"
GLAB_MR_IID="123"
GLAB_DISCUSSION_ID="discussion-id"
glab mr note resolve "$GLAB_MR_IID" "$GLAB_DISCUSSION_ID" -R "$GLAB_PROJECT"
```

```bash
GLAB_PROJECT="group/project"
GLAB_MR_IID="123"
GLAB_DISCUSSION_ID="discussion-id"
glab mr note reopen "$GLAB_MR_IID" "$GLAB_DISCUSSION_ID" -R "$GLAB_PROJECT"
```

List first, reply before resolving, and resolve only after the concern is addressed. Creating, replying, resolving, and reopening are separate mutations.

Use REST when the high-level command is unavailable or cannot express the operation. Use a numeric project ID or a URL-encoded project path in API routes.

List discussions or all notes:

```bash
GLAB_PROJECT_ID="12345"
GLAB_MR_IID="123"
glab api --paginate \
  "projects/$GLAB_PROJECT_ID/merge_requests/$GLAB_MR_IID/discussions" \
  | jq -c . | head -n 50
glab api --paginate \
  "projects/$GLAB_PROJECT_ID/merge_requests/$GLAB_MR_IID/notes?per_page=100" \
  | jq -c . | head -n 50
```

Reply to an existing discussion:

```bash
GLAB_PROJECT_ID="12345"
GLAB_MR_IID="123"
GLAB_DISCUSSION_ID="discussion-id"
GLAB_REPLY="Reply with the change and its verification."
glab api -X POST \
  "projects/$GLAB_PROJECT_ID/merge_requests/$GLAB_MR_IID/discussions/$GLAB_DISCUSSION_ID/notes" \
  -f "body=$GLAB_REPLY"
```

Resolve or reopen the discussion after replying:

```bash
GLAB_PROJECT_ID="12345"
GLAB_MR_IID="123"
GLAB_DISCUSSION_ID="discussion-id"
glab api -X PUT \
  "projects/$GLAB_PROJECT_ID/merge_requests/$GLAB_MR_IID/discussions/$GLAB_DISCUSSION_ID?resolved=true"
```

```bash
GLAB_PROJECT_ID="12345"
GLAB_MR_IID="123"
GLAB_DISCUSSION_ID="discussion-id"
glab api -X PUT \
  "projects/$GLAB_PROJECT_ID/merge_requests/$GLAB_MR_IID/discussions/$GLAB_DISCUSSION_ID?resolved=false"
```

Update a top-level note body only when explicitly requested:

```bash
GLAB_PROJECT_ID="12345"
GLAB_MR_IID="123"
GLAB_NOTE_ID="note-id"
GLAB_BODY="Replacement note body."
glab api -X PUT \
  "projects/$GLAB_PROJECT_ID/merge_requests/$GLAB_MR_IID/notes/$GLAB_NOTE_ID" \
  -f "body=$GLAB_BODY"
```

Never delete comments as routine cleanup.

## GraphQL note details

Use this exact query when the high-level and REST views cannot supply note IDs, edit timestamps, and bodies. Replace only the generic project path and MR IID.

```bash
glab api graphql -f query='
query {
  project(fullPath: "group/project") {
    mergeRequest(iid: "123") {
      notes(first: 20) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          lastEditedAt
          body
        }
      }
    }
  }
}'
```

If `hasNextPage` is true, rerun the query with `notes(first: 20, after: "END_CURSOR")`, replacing `END_CURSOR` with the returned cursor. Stop after 3 pages and report; continue only with explicit approval.

## Create or update an MR

Read [merge-requests.md](merge-requests.md) and render the description first.

```bash
GLAB_PROJECT="group/project"
GLAB_SOURCE_BRANCH="feature-branch"
GLAB_TARGET_BRANCH="target-branch"
GLAB_MR_TITLE="TICKET: concise imperative summary"
GLAB_ASSIGNEE="username"
GLAB_MR_DESCRIPTION="Rendered Summary, Testing, Deployment, Rollback, and Considerations."
glab mr create \
  -R "$GLAB_PROJECT" \
  --source-branch "$GLAB_SOURCE_BRANCH" \
  --target-branch "$GLAB_TARGET_BRANCH" \
  --title "$GLAB_MR_TITLE" \
  --assignee "$GLAB_ASSIGNEE" \
  --description "$GLAB_MR_DESCRIPTION" \
  --squash-before-merge \
  --remove-source-branch
```

On an existing MR, `glab mr update --squash-before-merge` and `--remove-source-branch` toggle the current value. Check it first and pass only the flags that are off:

```bash
GLAB_PROJECT="group/project"
GLAB_MR_IID="123"
glab mr view "$GLAB_MR_IID" -R "$GLAB_PROJECT" --output json \
  | jq '{squash, force_remove_source_branch}'
glab mr update "$GLAB_MR_IID" -R "$GLAB_PROJECT" --squash-before-merge   # only if squash is false
glab mr update "$GLAB_MR_IID" -R "$GLAB_PROJECT" --remove-source-branch  # only if force_remove_source_branch is false
```

Update the title and description together, or update only the assignee:

```bash
GLAB_PROJECT="group/project"
GLAB_MR_IID="123"
GLAB_MR_TITLE="TICKET: revised imperative summary"
GLAB_MR_DESCRIPTION="Revised rendered description."
glab mr update "$GLAB_MR_IID" \
  -R "$GLAB_PROJECT" \
  --title "$GLAB_MR_TITLE" \
  --description "$GLAB_MR_DESCRIPTION"
```

```bash
GLAB_PROJECT="group/project"
GLAB_MR_IID="123"
GLAB_ASSIGNEE="username"
glab mr update "$GLAB_MR_IID" -R "$GLAB_PROJECT" --assignee "$GLAB_ASSIGNEE"
```

Close or merge only after separate approval:

```bash
GLAB_PROJECT="group/project"
GLAB_MR_IID="123"
glab mr close "$GLAB_MR_IID" -R "$GLAB_PROJECT"
```

```bash
GLAB_PROJECT="group/project"
GLAB_MR_IID="123"
glab mr merge "$GLAB_MR_IID" -R "$GLAB_PROJECT" --squash --yes
```

## CI and pipelines

Check a branch pipeline and list recent pipelines:

```bash
GLAB_PROJECT="group/project"
GLAB_SOURCE_BRANCH="feature-branch"
glab ci status -R "$GLAB_PROJECT" --branch "$GLAB_SOURCE_BRANCH"
glab ci list -R "$GLAB_PROJECT"
```

Inspect one pipeline and one job log with the installed CLI syntax:

```bash
GLAB_PROJECT="group/project"
GLAB_PIPELINE_ID="12345"
glab ci get -R "$GLAB_PROJECT" --pipeline-id "$GLAB_PIPELINE_ID"
```

```bash
GLAB_PROJECT="group/project"
GLAB_JOB_ID="12345"
glab ci trace "$GLAB_JOB_ID" -R "$GLAB_PROJECT" | tail -n 100
```

Use REST when exact pipeline, job, commit-status, or MR-commit JSON is needed:

```bash
GLAB_PROJECT_ID="12345"
GLAB_MR_IID="123"
glab api "projects/$GLAB_PROJECT_ID/merge_requests/$GLAB_MR_IID/pipelines" \
  | jq -c . | head -n 50
glab api "projects/$GLAB_PROJECT_ID/merge_requests/$GLAB_MR_IID/commits?per_page=100" \
  | jq -c . | head -n 50
```

```bash
GLAB_PROJECT_ID="12345"
GLAB_PIPELINE_ID="12345"
glab api --paginate "projects/$GLAB_PROJECT_ID/pipelines/$GLAB_PIPELINE_ID/jobs" \
  | jq -c . | head -n 50
```

```bash
GLAB_PROJECT_ID="12345"
GLAB_COMMIT_SHA="commit-sha"
glab api --paginate \
  "projects/$GLAB_PROJECT_ID/repository/commits/$GLAB_COMMIT_SHA/statuses?per_page=100" \
  | jq -c . | head -n 50
```

Triggering, retrying, cancelling, or deleting CI state requires explicit approval.
