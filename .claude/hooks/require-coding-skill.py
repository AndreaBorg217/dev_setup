#!/usr/bin/env python3
"""Deny Edit/Write/MultiEdit on source files until the `coding` skill has been invoked."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

GATED_EXTENSIONS = {
    "py", "js", "ts", "tsx", "jsx", "go", "rs", "java", "kt", "rb", "php",
    "c", "cc", "cpp", "h", "hpp", "cs", "sh", "bash", "sql", "scala", "swift",
}

MARKER_ROOT = Path.home() / ".claude" / "skill-markers"

# A subagent's own Skill(coding) call can lag slightly behind the PreToolUse
# hook firing for its very next tool call, since the transcript write and the
# hook's read of that same file are not synchronized. Retry briefly before
# concluding the skill was never invoked, instead of denying on a stale read.
_RETRY_ATTEMPTS = 5
_RETRY_DELAY_SECONDS = 0.2


def _safe_id(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", raw)


def _marker_present(session_id: str, agent_id: str) -> bool:
    if not session_id:
        return False
    return (MARKER_ROOT / _safe_id(session_id) / _safe_id(agent_id) / "coding").exists()


def load_input() -> dict[str, Any]:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def file_extension(tool_input: dict[str, Any]) -> str:
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not path:
        return ""
    path = str(path)
    if "." not in path.rsplit("/", 1)[-1]:
        return ""
    return path.rsplit(".", 1)[-1].lower()


def _is_shebang_source(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """Treat an extensionless file as source if it starts with a shebang."""
    if tool_name == "Write":
        content = tool_input.get("content")
        first_line = content.splitlines()[0] if isinstance(content, str) and content else ""
    else:
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        try:
            with open(str(path), "r", encoding="utf-8", errors="replace") as handle:
                first_line = handle.readline()
        except OSError:
            first_line = ""
    return first_line.startswith("#!")


def _skill_invoked_now(transcript_path: str) -> bool:
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"name":"Skill"' not in line and '"name": "Skill"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                blocks = entry.get("message", {}).get("content") or []
                for block in blocks:
                    if not isinstance(block, dict) or block.get("name") != "Skill":
                        continue
                    skill = str((block.get("input") or {}).get("skill") or "")
                    if skill == "coding" or skill.endswith(":coding"):
                        return True
    except OSError:
        return False
    return False


def coding_skill_invoked(transcript_path: str) -> bool:
    for attempt in range(_RETRY_ATTEMPTS):
        if _skill_invoked_now(transcript_path):
            return True
        if attempt < _RETRY_ATTEMPTS - 1:
            time.sleep(_RETRY_DELAY_SECONDS)
    return False


def emit_deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
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

    if not (tool_input.get("file_path") or tool_input.get("notebook_path")):
        return 0

    extension = file_extension(tool_input)
    is_gated_extension = extension in GATED_EXTENSIONS
    is_gated_shebang = not extension and _is_shebang_source(tool_name, tool_input)
    if not is_gated_extension and not is_gated_shebang:
        return 0

    session_id = str(payload.get("session_id") or "")
    agent_id_raw = payload.get("agent_id")
    agent_id = str(agent_id_raw) if agent_id_raw else "main"

    if _marker_present(session_id, agent_id):
        return 0

    if agent_id_raw is None:
        transcript_path = payload.get("transcript_path")
        if transcript_path and coding_skill_invoked(str(transcript_path)):
            return 0

    emit_deny(
        "CODING_SKILL_REQUIRED: invoke the `coding` skill via the Skill tool "
        "before editing source files (per rules/coding.md)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
