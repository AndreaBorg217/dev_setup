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

## Merge requests

Find an MR by source branch before creating another one:

```bash
GLAB_PROJECT="group/project"
GLAB_SOURCE_BRANCH="feature-branch"
glab mr list \
  -R "$GLAB_PROJECT" \
  --source-branch "$GLAB_SOURCE_BRANCH" \
  --output json
```

Find MRs by author or search text:

```bash
GLAB_PROJECT="group/project"
GLAB_AUTHOR="username"
glab mr list -R "$GLAB_PROJECT" --author "$GLAB_AUTHOR" --all
```

```bash
GLAB_PROJECT="group/project"
GLAB_SEARCH="search text"
glab mr list -R "$GLAB_PROJECT" --search "$GLAB_SEARCH"
```

Inspect metadata, comments, structured fields, and the diff:

```bash
GLAB_PROJECT="group/project"
GLAB_MR_IID="123"
glab mr view "$GLAB_MR_IID" -R "$GLAB_PROJECT" --comments
glab mr view "$GLAB_MR_IID" -R "$GLAB_PROJECT" --output json
glab mr diff "$GLAB_MR_IID" -R "$GLAB_PROJECT"
```

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
  "projects/$GLAB_PROJECT_ID/merge_requests/$GLAB_MR_IID/discussions"
glab api --paginate \
  "projects/$GLAB_PROJECT_ID/merge_requests/$GLAB_MR_IID/notes?per_page=100"
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
      notes(first: 100) {
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

If `hasNextPage` is true, rerun the query with `notes(first: 100, after: "END_CURSOR")`, replacing `END_CURSOR` with the returned cursor. Continue until `hasNextPage` is false.

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
  --remove-source-branch
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
glab ci trace "$GLAB_JOB_ID" -R "$GLAB_PROJECT"
```

Use REST when exact pipeline, job, commit-status, or MR-commit JSON is needed:

```bash
GLAB_PROJECT_ID="12345"
GLAB_MR_IID="123"
glab api "projects/$GLAB_PROJECT_ID/merge_requests/$GLAB_MR_IID/pipelines"
glab api "projects/$GLAB_PROJECT_ID/merge_requests/$GLAB_MR_IID/commits?per_page=100"
```

```bash
GLAB_PROJECT_ID="12345"
GLAB_PIPELINE_ID="12345"
glab api --paginate "projects/$GLAB_PROJECT_ID/pipelines/$GLAB_PIPELINE_ID/jobs"
```

```bash
GLAB_PROJECT_ID="12345"
GLAB_COMMIT_SHA="commit-sha"
glab api --paginate \
  "projects/$GLAB_PROJECT_ID/repository/commits/$GLAB_COMMIT_SHA/statuses?per_page=100"
```

Triggering, retrying, cancelling, or deleting CI state requires explicit approval.
