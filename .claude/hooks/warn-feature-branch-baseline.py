#!/usr/bin/env python3
"""Advise when planning, implementation, or investigation starts on a feature branch."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_BRANCHES = {"main", "master", "prod", "production"}


def current_branch(cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "branch", "--show-current"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    branch = result.stdout.strip()
    return branch or None


def remote_default_branches(cwd: Path) -> set[str]:
    """Return branch names advertised by configured remote HEAD symbolic refs."""
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(cwd),
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


def main() -> int:
    try:
        payload: dict[str, Any] = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    cwd_raw = payload.get("cwd")
    if not isinstance(cwd_raw, str) or not cwd_raw:
        return 0
    cwd = Path(cwd_raw)
    branch = current_branch(cwd)
    known_bases = BASE_BRANCHES | remote_default_branches(cwd)
    if not branch or branch.lower() in known_bases:
        return 0
    message = (
        f"BRANCH_BASELINE_ADVISORY: current branch '{branch}' is not a recognized default or "
        "production branch. Before planning, implementation, or investigation, establish the "
        "correct baseline. Continue on this feature branch only when the user explicitly approved "
        "it for the current task. For investigation, use the verified requested default, production, "
        "or deployed ref without restoring feature changes onto it. For new work, ask whether to use "
        "this branch or branch from a verified base unless the user already specified the choice. "
        "When the user explicitly requests a named base or a new branch from it, inspect status, "
        "preserve dirty work with a scoped stash if needed, switch to and verify the requested base, "
        "create/check out the requested branch when applicable, and restore only changes that belong "
        "there. Do not assume a branch name or synchronization strategy. This is advisory only."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": message,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
