#!/usr/bin/env python3
import json
import sys
from pathlib import Path


event = json.load(sys.stdin)
if event["agent_type"] in {
    "caveman:cavecrew-investigator",
    "caveman:cavecrew-builder",
    "caveman:cavecrew-reviewer",
}:
    sys.exit()

style = (Path(__file__).resolve().parent / "../output-styles/Straight_to_the_Point.md").read_text()
if not style.startswith("---\n"):
    raise ValueError("output style has no YAML frontmatter")

style = style[style.index("\n---\n", 4) + 5 :]
json.dump(
    {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": style,
        }
    },
    sys.stdout,
)
