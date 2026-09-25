#!/usr/bin/env python3
"""Deny git-mutating Bash commands, and edits made on an unverified feature
branch, until the `git` skill has been invoked."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

MARKER_ROOT = Path.home() / ".claude" / "skill-markers"

# See require-coding-skill.py: a subagent's own Skill(git) call can lag
# slightly behind the PreToolUse hook firing for its very next tool call.
# Retry briefly before concluding the skill was never invoked.
_RETRY_ATTEMPTS = 5
_RETRY_DELAY_SECONDS = 0.2


def _safe_id(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", raw)


def _marker_present(session_id: str, agent_id: str) -> bool:
    if not session_id:
        return False
    return (MARKER_ROOT / _safe_id(session_id) / _safe_id(agent_id) / "git").exists()

GIT_MUTATING_COMMAND = re.compile(
    r"(?:^|[;&|]|\bcd\b[^;&|]*;)\s*"
    r"(?:[A-Za-z_][A-Za-z0-9_]*=\S+\s+)*"
    r"git\s+"
    r"(?:-C\s+\S+\s+|--git-dir=\S+\s+|--work-tree=\S+\s+)*"
    r"(?:"
    r"commit|push|merge|rebase|reset|tag|cherry-pick|pull|restore|clean"
    r"|branch\s+-[dD]"
    r"|checkout\s+-b"
    r"|switch\s+-[cC]"
    r"|stash\s+(?:pop|drop)"
    r")\b"
)

BASE_BRANCHES = {"main", "master", "prod", "production"}


def load_input() -> dict[str, Any]:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


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
                    if skill == "git" or skill.endswith(":git"):
                        return True
    except OSError:
        return False
    return False


def git_skill_invoked(transcript_path: str) -> bool:
    for attempt in range(_RETRY_ATTEMPTS):
        if _skill_invoked_now(transcript_path):
            return True
        if attempt < _RETRY_ATTEMPTS - 1:
            time.sleep(_RETRY_DELAY_SECONDS)
    return False


def current_branch(directory: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", directory, "branch", "--show-current"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    branch = result.stdout.strip()
    return branch or None


def remote_default_branches(directory: str) -> set[str]:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                directory,
                "for-each-ref",
                "--format=%(symref:short)",
                "refs/remotes",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    branches = set()
    for ref in result.stdout.splitlines():
        if "/" in ref:
            branches.add(ref.split("/", 1)[1].lower())
    return branches


def on_unverified_feature_branch(file_path: str) -> str | None:
    """Return the branch name if file_path sits on a non-baseline branch."""
    directory = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
    if not directory:
        return None
    branch = current_branch(directory)
    if not branch:
        return None
    known_bases = BASE_BRANCHES | remote_default_branches(directory)
    if branch.lower() in known_bases:
        return None
    return branch


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
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    transcript_path = payload.get("transcript_path")
    session_id = str(payload.get("session_id") or "")
    agent_id_raw = payload.get("agent_id")
    agent_id = str(agent_id_raw) if agent_id_raw else "main"

    if tool_name == "Bash":
        command = str(tool_input.get("command") or "")
        if not GIT_MUTATING_COMMAND.search(command):
            return 0
        if _marker_present(session_id, agent_id):
            return 0
        if agent_id_raw is None and transcript_path and git_skill_invoked(str(transcript_path)):
            return 0
        emit_deny(
            "GIT_SKILL_REQUIRED: invoke the `git` skill via the Skill tool "
            "before running a git-mutating command (per rules/interaction.md)."
        )
        return 0

    if tool_name in {"Edit", "Write", "MultiEdit"}:
        file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not file_path:
            return 0
        if _marker_present(session_id, agent_id):
            return 0
        if agent_id_raw is None and transcript_path and git_skill_invoked(str(transcript_path)):
            return 0
        branch = on_unverified_feature_branch(str(file_path))
        if not branch:
            return 0
        emit_deny(
            f"GIT_SKILL_REQUIRED: current branch '{branch}' is not a recognized "
            "default/production branch. Invoke the `git` skill via the Skill tool "
            "to confirm the baseline and get explicit user approval to edit on "
            "this feature branch before writing to a tracked file (per "
            "rules/interaction.md and the branch-baseline advisory)."
        )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
