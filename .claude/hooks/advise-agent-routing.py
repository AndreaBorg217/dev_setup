#!/usr/bin/env python3
"""Enforce worker model routing without rewriting Agent or Task inputs."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


LOCAL_AGENT_MODELS = {
    "artifact-writer": "haiku",
    "analyst": "sonnet",
    "builder": "sonnet",
    "explorer": "haiku",
}
MODEL_TIER = re.compile(r"(?:^|[^a-z])(haiku|sonnet|opus)(?=$|[^a-z])")


def load_input() -> dict[str, Any]:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def model_tier(value: Any) -> str:
    model = str(value or "").lower()
    tiers = set(MODEL_TIER.findall(model))
    if len(tiers) == 1:
        return tiers.pop()
    return ""


def validation_result(tool_input: dict[str, Any]) -> tuple[str, str] | None:
    agent_type = str(
        tool_input.get("subagent_type") or tool_input.get("type") or ""
    ).strip()
    model_value = tool_input.get("model")
    model_text = str(model_value or "").strip()
    if not model_text:
        return "deny", (
            "AGENT_MODEL_POLICY: every worker must declare model=haiku or "
            "model=sonnet. The main thread must choose the least expensive "
            "capable model for this task before dispatching it."
        )

    requested_model = model_tier(model_text)
    if not requested_model:
        return "deny", (
            f"AGENT_MODEL_POLICY: model={model_text!r} is not an allowed worker model. "
            "Choose model=haiku or model=sonnet based on the task's complexity."
        )
    if requested_model == "opus":
        return "ask", (
            "AGENT_MODEL_POLICY: an Opus worker requires explicit user approval for "
            "this call. Prefer Haiku or Sonnet unless the task's complexity justifies Opus."
        )

    expected_model = LOCAL_AGENT_MODELS.get(agent_type)
    if expected_model and requested_model != expected_model:
        return "deny", (
            f"AGENT_MODEL_POLICY: local agent {agent_type} requires model={expected_model}; "
            f"requested model={requested_model}. Use model={expected_model}."
        )
    return None


def emit_decision(decision: str, reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
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

    if tool_name not in {"Agent", "Task"}:
        return 0

    result = validation_result(tool_input)
    if result:
        emit_decision(*result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
