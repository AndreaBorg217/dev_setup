#!/usr/bin/env python3
"""Ask before a main-thread Edit/Write/MultiEdit touches a file that was
already delegated to a subagent this session (rules/subagents.md file
ownership continuity)."""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

AGENT_TOOL_LINE = re.compile(r'"name"\s*:\s*"Agent"')


def load_input() -> dict[str, Any]:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def delegated_to_subagent(transcript_path: str, basename: str) -> bool:
    pattern = re.compile(re.escape(basename))
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if AGENT_TOOL_LINE.search(line) and pattern.search(line):
                    return True
    except OSError:
        return False
    return False


def emit_ask(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def main() -> int:
    payload = load_input()
    tool_name = str(payload.get("tool_name") or "")
    if tool_name not in {"Edit", "Write", "MultiEdit"}:
        return 0

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not file_path:
        return 0
    basename = os.path.basename(str(file_path))

    transcript_path = payload.get("transcript_path")
    if not transcript_path:
        return 0

    if delegated_to_subagent(str(transcript_path), basename):
        emit_ask(
            f"FILE_OWNERSHIP_CONTINUITY: '{basename}' was already delegated to a "
            "subagent this session. Route this edit back to that owner via "
            "SendMessage instead of editing it from the main thread, unless the "
            "owner is unavailable or demonstrably failed (per rules/subagents.md)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
