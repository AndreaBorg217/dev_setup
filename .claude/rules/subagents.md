# Subagents

- Route by task and set the Agent `model` parameter explicitly; do not inherit Opus by default.
- Prefer caveman agents with compressed output whenever one fits.

| Task | Model | Prefer agent |
|------|-------|--------------|
| Search, locate, read, "where is X", "what calls Y", map a directory | `haiku` | `caveman:cavecrew-investigator` |
| Loops, polling | `haiku` | `claude` |
| Implementation or edits | `sonnet` | `caveman:cavecrew-builder` for 1-2 files |
| Planning | `opus` | `Plan` |
