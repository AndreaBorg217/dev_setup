# Git CLI reference

Replace uppercase placeholders with verified values. Use `--` before pathspecs.

## State and refs

Resolve the repository, `HEAD`, and upstream:

```bash
git rev-parse --show-toplevel
git rev-parse --is-inside-work-tree
git rev-parse --abbrev-ref HEAD
git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'
git symbolic-ref --short HEAD
```

Inspect the worktree and index:

```bash
git status --short
git status --short --branch
git status --porcelain=v1
git status --short --ignored
```

Check a remote ref without fetching it. This prints refs, not the remote URL:

```bash
git ls-remote REMOTE REF
```

Resolve tracked, untracked, and ignored paths:

```bash
git ls-files -- PATH
git ls-files --others --exclude-standard
git check-ignore -v PATH
```

## Diffs and history

Check scope, whitespace, staged content, or arbitrary paths:

```bash
git diff --check
git diff --stat TARGET...HEAD
git diff --name-status TARGET...HEAD
git diff TARGET...HEAD -- PATH
git diff --staged --stat
git diff --staged --name-only
git diff --no-index -- PATH_A PATH_B
git diff --quiet -- PATH
```

Three dots show feature work since the merge base. `--no-index` also compares untracked files. `--quiet` reports through its exit code.

Find historical changes without scanning every commit:

```bash
git log --oneline -20
git log --oneline --all -- PATH
git log --follow --oneline -- PATH
git log --all -S'STRING' --oneline -- PATH
git log --all -G'REGEX' -p -- PATH
git log --all --grep='PATTERN' -i --oneline
git log --since='START' --until='END' --oneline -- PATH
git log --diff-filter=ADR --name-only --oneline -- PATH
git log -L START,END:PATH
git log OLD..NEW --ancestry-path --oneline
git log --reverse --format='%h %s' -- PATH
```

`-S` tracks exact-string count changes. `-G` matches changed lines. `-L` follows a line range or function. `--ancestry-path` keeps commits between two revisions.

Inspect commits, files, and objects without changing the worktree:

```bash
git show --stat COMMIT
git show COMMIT -- PATH
git show COMMIT:PATH
git show -m COMMIT -- PATH
git cat-file -t OBJECT
git cat-file -e OBJECT
git hash-object -t blob PATH
git grep -n 'PATTERN' -- PATH
git grep -l 'PATTERN'
git ls-tree -r COMMIT --name-only
git ls-tree COMMIT -- PATH
```

`show -m` exposes a merge commit against each parent. `cat-file -e` checks existence without printing content. `hash-object` calculates an object ID without writing it unless `-w` is added.

Establish ancestry, divergence, and likely conflicts:

```bash
git merge-base HEAD TARGET
git merge-base --is-ancestor COMMIT TARGET
git rev-list --left-right --count TARGET...HEAD
git merge-tree "$(git merge-base HEAD TARGET)" HEAD TARGET
```

## Stashes and worktrees

Protect only the intended changes:

```bash
git stash push -m "context and reason" -- PATH
git stash push -u -m "context and reason"
git stash push --keep-index -- PATH
git stash list
git stash show --stat stash@{N}
git stash show -p stash@{N} -- PATH
git stash apply stash@{N}
git stash pop stash@{N}
git stash drop stash@{N}
```

`-u` includes untracked files. `--keep-index` leaves staged work in place. Use `apply` when the backup should remain. Recheck `stash list` after a drop because positions change.

Isolate another ref:

```bash
git worktree list
git worktree add WORKTREE_PATH EXISTING_REF
git worktree add -b NEW_REF WORKTREE_PATH START_POINT
git worktree add --detach WORKTREE_PATH COMMIT
git worktree remove WORKTREE_PATH
git worktree prune
```

Inspect a worktree before removal. Use `--force` only after explicit approval for that exact path.

## Synchronize and rewrite

Refresh remote-tracking refs without changing the worktree:

```bash
git fetch REMOTE TARGET --quiet
git fetch --all --quiet
```

Allow only linear updates:

```bash
git pull --ff-only REMOTE TARGET
git merge --ff-only REF
git merge --abort
```

Start a temporary integration merge when `merge-tree` is insufficient:

```bash
git merge --no-commit --no-ff REF
git merge --abort
```

Start clean and obtain approval before the mutating merge check.

Replay feature work or one selected change:

```bash
git rebase TARGET
git cherry-pick COMMIT
```

Fetch the verified target before rebasing. Stop when conflict intent is unclear.

Reverse published changes without rewriting shared history:

```bash
git revert --no-edit COMMIT
git revert --no-commit COMMIT_RANGE
```

`--no-commit` prepares the inverse changes for review.

Reconstruct local state:

```bash
git reset -- PATH
git reset --soft HEAD^
```

The path form unstages without changing the file. A soft reset keeps the previous commit's changes staged. `git reset --hard REF` discards index and worktree changes and requires exact-target verification plus explicit approval.

## Patches and recovery

Preflight an external patch:

```bash
git apply --check PATCH_FILE
git apply PATCH_FILE
```

Recover moved or unreachable objects:

```bash
git reflog
git reflog --all
git reflog show REF --date=iso -20
git fsck --no-reflog --unreachable --dangling
git rev-list --objects --all
```

Inspect release containment and refs:

```bash
git show-ref
git tag --contains COMMIT
```

Delete one verified stale ref:

```bash
git update-ref -d REF
```

Verify the fully qualified ref and obtain approval first.
