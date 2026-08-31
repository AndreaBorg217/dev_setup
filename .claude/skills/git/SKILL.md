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

## Keep history reviewable

- Match the repository's commit convention. When a ticket key exists, use `TICKET: concise imperative summary` and preserve its casing.
- Keep commits small and logical. Amend corrections into their logical commit instead of retaining false-start or review-fix commits.
- Rebase feature work onto the verified target. Do not merge the target into the feature branch.
- After rewritten history, use force-with-lease. Never use an unguarded force update.
- Commit at useful review boundaries and push in bulk to avoid unnecessary CI/CD churn.

## Voice

Write commit messages in `Straight_to_the_Point` voice: plain, direct sentences stating what changed and why. No filler, no padding.

## Approval

Skill invocation does not authorize a mutation. Read-only inspection may run when relevant. Obtain explicit QA and approval immediately before commits, pushes, ref changes, stash removal, worktree removal, history rewrites, destructive recovery, remote configuration changes, and other conclusive operations.

Never expose credentials, tokens, private keys, or credential-bearing remote URLs.
