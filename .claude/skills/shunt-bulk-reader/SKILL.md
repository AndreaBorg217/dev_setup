---
name: shunt-bulk-reader
description: "Delegate bulk file reading to Haiku. Use when you need to read files >350 lines, answer questions across 3+ files, or summarize large diffs. Replaces Spotify shunt's AiKA bulk-reader with local Haiku."
when_to_use: "bulk-read, Haiku subagent, shunt, bulk-read script, SHUNT_MIN_LINES, SHUNT_TIMEOUT_SECONDS, SHUNT_MAX_PAYLOAD_BYTES, check-file-size hook, check-bash-read hook, large diff summary, read files over 350 lines, questions across multiple files, ctx_batch_execute, ctx_search, intent filter, Not logged in fallback, grep outline fallback, Task subagent_type general model haiku, follow-up bulk-read, Read offset limit verify"
---

# Shunt Bulk Reader (Haiku)

Delegate I/O-heavy reads to the cheaper Haiku model so Opus/Sonnet context stays lean.

## Preferred: Haiku subagent (no external dependency)

Per `rules/subagents.md`, use the `explorer` Haiku agent with Context Mode sandbox — this is the canonical Haiku worker:

```
Task(subagent_type="general", model="haiku", prompt="Bulk-read: <question>. Paths: <file1> <file2>. Use ctx_batch_execute to gather files, ctx_search + intent filter to extract only what answers the question. Return compact bullets with exact names/line numbers; keep raw output in sandbox. Never return full files.")
```

Follow-up: dispatch again with same paths + new question — re-sending to Haiku costs nothing to Opus.

## Alternative: Local bash script (shunt-compatible)

When a direct script is desired (mirrors Spotify shunt's flow but with Haiku fallback):

```bash
~/Documents/GitHub/dev_setup/.claude/scripts/shunt/bulk-read --question "<question>" --paths <file1> [<file2> ...]
```

- Wraps each file in `<file path="...">` XML.
- Calls `lib/haiku.sh:shunt_invoke bulk-reader` → `claude -p --model haiku --no-session-persistence --tools "" --system-prompt "<bulk-reader prompt>"` with `SHUNT_TIMEOUT_SECONDS=180`, `SHUNT_MAX_PAYLOAD_BYTES=400000`.
- If Haiku auth unavailable (`Not logged in`), falls back to deterministic `grep -n "class|def|export|function"` outline — still ~80% token savings vs full read.
- Reports `~chars/4` tokens to stderr.

Each call is independent. To ask a follow-up, ask again with the same `--paths` — files go to Haiku, never into Opus context.

**Verify:** Haiku summaries are lossy. Confirm specific line numbers or exact values with targeted `Read(offset, limit)` before editing.

## When NOT to delegate (from upstream `What doesn't get delegated`)

- Debugging (needs Opus reasoning)
- Editing (needs exact content — use `Read` with `offset`/`limit`, which Shunt intentionally allows)
- Small files ≤ `SHUNT_MIN_LINES` (default 350, override via `env.SHUNT_MIN_LINES` in `settings.json`)
- Architectural decisions

## Hook

`hooks/check-file-size` blocks `Read` on >350 lines; `hooks/check-bash-read` blocks `cat/head/tail` on large files. Piped `cat file | grep` and redirections pass through as targeted reads.
