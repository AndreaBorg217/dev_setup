#!/usr/bin/env python3
"""Nudge (ask, never deny) when the main trace exceeds the request threshold once per session."""

from __future__ import annotations

import json
import sys
from typing import Any

MAX_MAIN_REQUESTS = 25


def load_input() -> dict[str, Any]:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def count_main_requests(transcript_path: str) -> int:
    count = 0
    with open(transcript_path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, RecursionError):
                continue
            if isinstance(event, dict) and event.get("type") == "assistant":
                count += 1
    return count


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
    if tool_name not in {"Bash", "Read", "Edit", "Write", "Grep", "Glob"}:
        return 0

    transcript_path = payload.get("transcript_path")
    if not transcript_path:
        return 0
    transcript_path = str(transcript_path)
    marker_path = transcript_path + ".excessive_main_requests_notified"

    try:
        import os

        if os.path.exists(marker_path):
            return 0

        main_requests = count_main_requests(transcript_path)
        if main_requests <= MAX_MAIN_REQUESTS:
            return 0

        with open(marker_path, "w", encoding="utf-8") as handle:
            handle.write("notified\n")
    except OSError:
        return 0

    emit_ask(
        f"SESSION_EFFICIENCY: main trace has made {main_requests} model requests "
        f"(reference: {MAX_MAIN_REQUESTS}). Consider delegating remaining work to "
        "explorer/analyst/builder via the Agent tool per rules/subagents.md."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
