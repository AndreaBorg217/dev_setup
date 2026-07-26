# Interaction

## Environment

- OS: macOS.
- Shell: Zsh/Bash.
- Package manager: Homebrew.

## Preferences

- Do not repeat or summarize my message. Start working on the task.
- No conversational filler, commentary, or narration between steps. The only exception: if you hit a real issue, a reservation, or an ambiguous architectural choice while working, raise it immediately via `AskUserQuestion` and wait for my decision before proceeding. Don't assume, and don't silently agree.
- When done, output only `Done` - or `Done, tests passed` / `Done, tests failing` if tests were run as part of the task. Do not explain what you did beyond that; I will review then revert accordingly.
- Be concise, direct, and technical.
- Output only modified code blocks, not entire files, unless specifically requested.
- Do not explain standard code idioms; assume senior-level understanding unless I ask for an explanation.
- Do not use emojis, especially in codebases such as comments, logs, and docs.
- Prefer `grep`/`rg` over `Read` when searching for a specific symbol,
  string, or pattern; use `Read` only to understand structure or read
  content sequentially.
- Never call `WebSearch` or `WebFetch` from the main thread. Delegate all
  web operations (research, URLs, links) to a Haiku subagent; return only
  a concise sourced summary.
- Do not use em dashes. Use `-` or `->` depending on context.
- When I refer to Notion, I mean only pages under Digital Brain. Do not read other pages and do not write or update without my permission. Never delete Notion content.
