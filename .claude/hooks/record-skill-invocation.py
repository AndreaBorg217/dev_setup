#!/usr/bin/env python3
"""Record a session- and agent-scoped marker when a skill is invoked.

require-coding-skill.py and require-git-skill.py gate Edit/Write/MultiEdit
(and git-mutating Bash) on a skill having been invoked first. They decide
this by re-scanning the transcript file for a prior Skill tool_use, keyed by
transcript_path. For a subagent, the transcript_path seen by the gate on its
very next tool call has been observed to not yet contain that subagent's own
Skill-call turn, causing the gate to deny even right after the skill was
invoked. A marker file written here, at the moment the skill is invoked,
removes that dependency: the gates check the marker (keyed by session_id and
agent_id, which are stable across a subagent's own tool calls) before falling
back to a transcript scan.

Two hook event shapes are handled:
- PostToolUse Skill: the skill name comes from tool_input.skill.
- UserPromptExpansion (a typed slash command, e.g. "/coding"): the skill name
  comes from command_name, with any plugin namespace prefix stripped.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

MARKER_ROOT = Path.home() / ".claude" / "skill-markers"


def load_input() -> dict[str, Any]:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def safe_id(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", raw)


def skill_from_payload(payload: dict[str, Any]) -> str:
    tool_name = str(payload.get("tool_name") or "")
    if tool_name == "Skill":
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            return ""
        return str(tool_input.get("skill") or "").strip()

    command_name = payload.get("command_name")
    if command_name:
        return str(command_name).strip()

    return ""


def record_marker(session_id: str, agent_id: str, skill: str) -> None:
    # Plugin-scoped skills ("plugin:coding") mark under their bare name too.
    skill_name = skill.rsplit(":", 1)[-1]

    marker_dir = MARKER_ROOT / safe_id(session_id) / safe_id(agent_id)
    marker_dir.mkdir(parents=True, exist_ok=True)
    (marker_dir / safe_id(skill_name)).touch()


def main() -> int:
    payload = load_input()
    skill = skill_from_payload(payload)
    session_id = str(payload.get("session_id") or "").strip()
    if not skill or not session_id:
        return 0

    agent_id = str(payload.get("agent_id") or "main").strip() or "main"
    record_marker(session_id, agent_id, skill)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
