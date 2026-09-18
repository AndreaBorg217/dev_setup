#!/usr/bin/env python3
"""Advise on missing planner steps without blocking ExitPlanMode."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_events(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    events = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    events.append(event)
    except OSError:
        return []
    return events


def tool_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls = []
    failed: set[str] = set()
    for event in events:
        message = event.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), list):
            continue
        for block in message["content"]:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                calls.append(block)
            elif block.get("type") == "tool_result" and block.get("is_error"):
                failed.add(str(block.get("tool_use_id") or ""))
    for call in calls:
        call["failed"] = str(call.get("id") or "") in failed
    return calls


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    raw_path = payload.get("transcript_path") if isinstance(payload, dict) else None
    path = Path(raw_path).expanduser() if isinstance(raw_path, str) else None
    calls = tool_calls(load_events(path))

    seen_template = {"plan-template.md": False, "task-template.md": False}
    writer = False
    reviewer = False
    validator = False
    for call in calls:
        name = str(call.get("name") or "")
        tool_input = call.get("input") if isinstance(call.get("input"), dict) else {}
        rendered = json.dumps(tool_input, ensure_ascii=False).lower()
        for template in seen_template:
            if name == "Read" and template in rendered and not call["failed"]:
                seen_template[template] = True
        if name in {"Agent", "Task"}:
            agent_type = str(tool_input.get("subagent_type") or tool_input.get("type") or "").lower()
            model = str(tool_input.get("model") or "").lower()
            prompt = str(tool_input.get("prompt") or tool_input.get("description") or "").lower()
            if agent_type == "artifact-writer" and "haiku" in model:
                writer = True
            if agent_type == "explorer" and "haiku" in model:
                reviewer = reviewer or (
                    "review" in prompt and ("plan" in prompt or "bundle" in prompt)
                )
        if name == "Bash":
            command = str(tool_input.get("command") or "")
            if "materialize_plan_bundle.py" in command and "--check" in command and not call["failed"]:
                validator = True

    missing = [name for name, seen in seen_template.items() if not seen]
    if not writer:
        missing.append("Haiku artifact-writer")
    if not reviewer:
        missing.append("Haiku explorer review")
    if not validator:
        missing.append("successful plan validator check")
    if not missing:
        return 0

    message = (
        "PLAN_ADVISORY: before ExitPlanMode, consider correcting: "
        + ", ".join(missing)
        + ". This is advisory only; do not block the user from exiting plan mode."
    )
    print(json.dumps({"continue": True, "systemMessage": message}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
