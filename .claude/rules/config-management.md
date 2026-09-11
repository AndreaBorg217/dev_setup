# Config Management

All Claude and tool configs are managed in `~/Documents/GitHub/dev_setup/` and tracked in git.

- Edit `~/Documents/GitHub/dev_setup/.claude/`, not `~/.claude/`, even when invoked from another project.
- This includes `.claude/settings.json` (the source for
  `~/.claude/settings.json`), `CLAUDE.md`, `rules/`, `skills`, `scripts`, and
  `statusline.sh`. Machine-specific MCP registrations remain in Claude's
  mutable runtime configuration and are managed through the Claude CLI.
