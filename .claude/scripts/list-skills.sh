#!/usr/bin/env bash
# Lists all skills with their name and description from SKILL.md frontmatter
find ~/Documents/GitHub/dev_setup/.claude/skills -name "SKILL.md" | sort | while read -r f; do
    echo "=== $f ==="
    head -5 "$f"
    echo
done
