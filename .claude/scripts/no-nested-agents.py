#!/usr/bin/env python3
"""PreToolUse hook, matcher "Agent". Denies Agent-tool calls made from inside
a subagent (agent_id present in stdin JSON), keeping subagents leaf-tier.
Main-thread Agent calls (no agent_id) pass through untouched.
Escape hatch: CLAUDE_ALLOW_NESTED_AGENTS=1 disables the check.
"""
import json
import os
import sys


def main():
    if os.environ.get("CLAUDE_ALLOW_NESTED_AGENTS") == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if not payload.get("agent_id"):
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "Nested subagents are disabled (rules/subagents.md: subagents "
                "are leaf-tier). Do the work yourself and return a summary, or "
                "return a proposed split for the orchestrator - the main "
                "thread fans out, using the Workflow tool when the fan-out is "
                "large."
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
