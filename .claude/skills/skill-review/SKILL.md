---
name: skill-review
description: Review the current session transcript for skill usage, consolidation opportunities, and missing reusable workflows. Use when asked to review, improve, consolidate, or propose Claude Code skills based on the current session.
---

# Skill Review

Analyze the current session transcript to improve the skill set in `~/Documents/GitHub/dev_setup/.claude/skills/`.

## Steps

1. Parse only the current session transcript:
   - Run `~/.claude/scripts/parse-transcript.sh` with no arguments.
   - Do not read other transcripts.
   - The script defaults to the most recently modified `.jsonl`, which is the current session.

2. List existing skills:
   - Run `~/.claude/scripts/list-skills.sh`.

3. Consolidate used skills:
   - Review which skills from `~/.claude/skills/` were triggered this session.
   - Look for overlap, redundancy, missing provisions based on directions I gave, or skills that could be merged.
   - Propose updated `SKILL.md` files where appropriate.

4. Propose new skills:
   - Identify recurring multi-step workflows in this session that are not covered by existing skills.
   - For each proposed skill, draft a complete `SKILL.md` with name, description, and instructions.
   - Follow the skill-creator process for proper `SKILL.md` structure.

## Output

- Provide a consolidation report.
- Include draft `SKILL.md` files for any new or updated skills.
- All file writes must target `~/Documents/GitHub/dev_setup/.claude/`; never write to `~/.claude/` directly.
