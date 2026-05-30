Analyze the current session's transcript to:

1. **Consolidate used skills**: Review which skills from `~/.claude/skills/` were triggered this session. Look for overlap, redundancy, missing provisions based on directions I gave, or skills that could be merged. Propose updated SKILL.md files.

2. **Propose new skills**: Identify recurring multi-step workflows in this session that aren't covered by existing skills. For each, draft a new `SKILL.md` with name, description, and instructions.

Steps:
- Parse the current session only: `~/.claude/scripts/parse-transcript.sh` (no args — defaults to the most recently modified .jsonl, which is always the current session). Do NOT read other transcripts.
- List existing skills: `~/.claude/scripts/list-skills.sh`
- Output: a consolidation report + draft SKILL.md files for any new skills
- For each new skill, follow the skill-creator process to write a proper SKILL.md
- All file writes (new or updated SKILL.md, settings, CLAUDE.md) must target `~/Documents/GitHub/dev_setup/.claude/` — never `~/.claude/`
