#!/usr/bin/env python3
"""Offer non-blocking guidance for efficient agent and discovery routing."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


LOCAL_AGENT_MODELS = {
    "artifact-writer": "haiku",
    "builder": "sonnet",
    "explorer": "haiku",
}
SEARCH_COMMAND = re.compile(
    r"(?:^|[;&|]\s*)(?:fd|find|grep|head|ls|rg|sed|stat|tail|tree|wc)\b"
    r"|(?:^|[;&|]\s*)git\s+(?:log|ls-files|show)\b",
    re.IGNORECASE,
)


def load_input() -> dict[str, Any]:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def model_tier(value: Any) -> str:
    model = str(value or "").lower()
    for tier in ("haiku", "sonnet", "opus"):
        if tier in model:
            return tier
    return ""


def is_subagent(transcript_raw: Any) -> bool:
    if not isinstance(transcript_raw, str):
        return False
    return "subagents" in Path(transcript_raw).parts


def agent_advisory(tool_input: dict[str, Any]) -> str:
    agent_type = str(tool_input.get("subagent_type") or "")
    requested_model = model_tier(tool_input.get("model"))
    expected_model = LOCAL_AGENT_MODELS.get(agent_type)
    if expected_model and requested_model != expected_model:
        return (
            f"ROUTING_ADVISORY: local agent {agent_type} is designed for model={expected_model}. "
            "This is guidance only; continue with another model when the task warrants it."
        )
    if not requested_model:
        return (
            "ROUTING_ADVISORY: no model was specified for this worker, so runtime defaults may "
            "route it to Sonnet. Consider model=haiku for bounded read-only collection. "
            "This is guidance only and does not restrict the chosen agent type."
        )
    return ""


def discovery_advisory(tool_name: str, tool_input: dict[str, Any]) -> str:
    discovery = tool_name in {"Glob", "Grep"}
    if tool_name == "Read":
        discovery = not tool_input.get("offset") and not tool_input.get("limit")
    if tool_name == "Bash":
        command = str(tool_input.get("command") or "")
        discovery = bool(SEARCH_COMMAND.search(command))
    if not discovery:
        return ""
    return (
        "ROUTING_ADVISORY: for bounded read-only repository discovery, consider delegating to "
        "an explorer with model=haiku and returning only compact evidence. This is guidance only; "
        "continue in the main thread when direct inspection is more appropriate."
    )


def emit_advisory(message: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": message,
                }
            }
        )
    )


def main() -> int:
    payload = load_input()
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    if tool_name in {"Agent", "Task"}:
        message = agent_advisory(tool_input)
    elif is_subagent(payload.get("transcript_path")):
        message = ""
    else:
        message = discovery_advisory(tool_name, tool_input)
    if message:
        emit_advisory(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
