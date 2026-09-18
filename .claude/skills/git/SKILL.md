---
name: git
description: Manages Git operations - status, diff, commits, branches and history rewrites. Use when inspecting or mutating Git state.
---

# Git

Load this skill once before the first `git` command in a task. Keep its instructions active for the rest of that task.

## Use the reference

Read the relevant section of [references/git-cli.md](references/git-cli.md) before running a Git command. It contains the selected problem-solving commands, safe examples, and recovery limits.

## Establish the state

Resolve the repository root, current branch, status, relevant diffs, remotes, upstream, target branch, stashes, and worktrees that the operation can affect. Derive the actual target from repository evidence. Never assume its name. Ask the user for branch name and commit prefix if unsure, never assume a default.

Preserve unrelated and pre-existing work. Do not overwrite, stage, restore, commit, or include it without explicit approval.

Before planning, implementation, or investigation, establish the correct base.
Do not use a feature branch for the task unless the user explicitly approves that
branch. Resolve the repository's actual default, production, or deployed ref from
evidence; never assume it is named `main` or `master`.

For an investigation, use the verified ref that represents the state being
investigated. If the user names `main`, `master`, a production branch, or another
base, preserve dirty work as needed and switch to that verified ref; do not
restore feature-branch changes onto the investigation baseline.

For new work, ask whether to continue on the current feature branch or branch
from a verified base unless the user already made that choice. An explicit request
to create a branch from a named base authorizes the necessary local transition:
inspect status, preserve dirty work with a scoped stash when needed, switch to and
verify the base, create and check out the requested branch, then restore only the
changes that belong on the new branch. Stop for unclear stash ownership, conflicts,
an unknown branch name, or a base that is behind or diverged.

## Synchronize before change work

Before source discovery or edits for a new change, inspect the worktree, branch,
upstream, and divergence, then fetch the verified upstream or target ref. Fetch
does not authorize a pull or history rewrite. If the worktree is dirty, no
upstream/target is established, the local branch is behind or diverged, or the
next safe step could be pull, rebase, stash, reset, or conflict resolution, use
`AskUserQuestion` with the observed state and consequences. Wait for the answer;
never select a synchronization strategy because it is conventional.

## Keep history reviewable

- Match the repository's established commit convention.
- Keep commits small and logical. Amend corrections into their logical commit instead of retaining false-start or review-fix commits.
- Rebase feature work onto the verified target. Do not merge the target into the feature branch.
- After rewritten history, use force-with-lease. Never use an unguarded force update.
- Commit at useful review boundaries and push in bulk to avoid unnecessary CI/CD churn.

## Approval

Skill invocation does not authorize a mutation. Read-only inspection and a
fetch from an already-configured, verified remote/ref may run as synchronization
preflight. Obtain explicit QA and approval immediately before commits, pushes,
local branch/tag changes, stash removal, worktree removal, pull/rebase/history
rewrites, destructive recovery, remote configuration changes, and other
conclusive operations.

Never expose credentials, tokens, private keys, or credential-bearing remote URLs.
