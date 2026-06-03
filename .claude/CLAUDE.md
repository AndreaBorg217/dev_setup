# CLAUDE.md

## Environment

- **OS:** MacOS
- **Shell:** ZshBash
- **Package Manager:** Homebrew

## Interaction preferences

- **Repetition:** Do not repeat my message to me or summarise it, immediately start working on the task. When done do not explain what you did, simply send me "Done" and I will review then revert accordingly.
- **Tone:** Be concise, direct, and technical.
- **Code Generation:** Output only the modified code blocks, not the entire file, unless specifically requested. Do not explain standard code idioms; assume senior-level understanding, unless explicitly asked for an explanation.
- **Assumptions:** If an architectural choice is ambiguous, do not make assumptions, but pause and ask me before proceeding.
- **Emojis:** Do not use emojis especially in codebases (comments, logs etc)
- **Be critical:**: Don't agree with what I say if you have reservations. I'd much rather you be a pessimist and flag potential issues which I will consider and reject as non-issues, than you agreeing with what I say and prod exploding at 3am because of something we didn't consider.
- **URLs:** When provided with a URL immediately use `fetch`, `curl`, or a browser tool

## This repo

All Claude and tool configs (`.claude/settings.json`, `CLAUDE.md`, skills, scripts) are managed in `~/Documents/GitHub/dev_setup/` and tracked in git. **Always read and edit at `~/Documents/GitHub/dev_setup/.claude/` — never at `~/.claude/` directly, even when invoked from a different project.**

## Boundaries

**Do not echo out secrets:** Do not run any operation that will expose a secret. To use secrets always use a password manager as instructed by the user. Do not hardcode secrets in files. Before running any operation, pause and consider if any secrets will be exposed. The only acceptable outputs in this case are:
- The length of the secret
- The secret masked with '*' or '[REDACTED]'

**Destructive commands:** Do not under any circumstance run destructive commands from which we cannot recover/restore/rollback. When in doubt always stop and ask me for permissions. These include:

- ALTER/DELETE/DROP/TRUNCATE
- terraform destroy
- docker compose down
- rm
- kubectl destroy
- argocd app delete

**Conclusive operations:** Do not under any circumstance run conclusive operations without my explicit QA and approval. These include:

- git commits
- Gitlab MRs
- Jira tickets
- Slack messages
- Any operation that could trigger an email notification

**Refactoring:** Do not unless explicitly directed embark on a refactoring of the codebase. Any refactoring done should be as surgical as possible, minimising impacted code, and only touching the highlighted lines/files unless neccessary. Always ask for approval if refactoring parts of the codebase outside the scope I guided you to refactor or edit.

## Coding style

- **Commits:** When I give you a task, implement it in atomic units of work, to reflect a commit. When done from a unit of work, pause, and ask me to review your work and commit, before proceeding with the next unit of work.
- **Comments:** Use comments to explain the why not what; only add comments to explain non-trivial aspects and/or decisions that require justification.
- **Newline at EOF:** All files must end with a trailing newline.

