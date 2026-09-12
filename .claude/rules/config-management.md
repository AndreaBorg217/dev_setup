# Config Management

All Claude and tool configs are managed in `~/Documents/GitHub/dev_setup/` and tracked in git.

- Edit `~/Documents/GitHub/dev_setup/.claude/`, not `~/.claude/`, even when invoked from another project.
- This includes `.claude/settings.json` (the source for
  `~/.claude/settings.json`), `CLAUDE.md`, `rules/`, `skills`, `scripts`, and
  `statusline.sh`. Machine-specific MCP registrations remain in Claude's
  mutable runtime configuration and are managed through the Claude CLI.
- Consolidate before adding: prefer improving an existing skill, rule, or config over adding a new file, rule, or concept. Before adding config, check in order: (1) does it need to exist (YAGNI)? (2) does an existing skill/rule already cover it? (3) can an existing file be amended instead? New concepts require evidence and increase model confusion — the leaner and most direct option is preferred. Direct analogue of `skills/coding:11-31` for configuration.
