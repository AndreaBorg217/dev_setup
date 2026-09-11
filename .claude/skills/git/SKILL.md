---
name: git
description: Use when any Git operation is requested, including read-only repository inspection (status, log, diff, blame) and history changes (commit, revert, reset, rebase, amend, cherry-pick, stash, force-push, branch/tag delete).
---

# Git

Load this skill once before the first `git` command in a task. Keep its instructions active for the rest of that task.

## Use the reference

Read the relevant section of [references/git-cli.md](references/git-cli.md) before running a Git command. It contains the selected problem-solving commands, safe examples, and recovery limits.

## Establish the state

Resolve the repository root, current branch, status, relevant diffs, remotes, upstream, target branch, stashes, and worktrees that the operation can affect. Derive the actual target from repository evidence. Never assume its name.

Preserve unrelated and pre-existing work. Do not overwrite, stage, restore, commit, or include it without explicit approval.

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
