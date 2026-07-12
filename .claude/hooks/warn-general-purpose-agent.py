#!/usr/bin/env python3
"""
PreToolUse Hook: Nudges away from high-cost subagent types toward cheaper,
purpose-built plugin agents.

- general-purpose: tools:* with uncompressed output - largest token sink.
- Explore: uncompressed broad search - prefer cavecrew-investigator for
  pure locate/"where is X"/"what calls Y" tasks (compressed output, strictly
  cheaper). Confirm Explore only when scope is genuinely broad/analytical
  (investigator refuses analysis and returns lossy output, so it's wrong there).
"""

import json
import sys

NUDGES = {
    "general-purpose": (
        "general-purpose is tools:* with uncompressed output - the biggest token "
        "sink among subagents. Prefer: caveman:cavecrew-investigator (locate code), "
        "caveman:cavecrew-builder (1-2 file edit), caveman:cavecrew-reviewer (diff review), "
        "Explore (broad analysis), Plan (planning), claude-code-guide (CC/API/SDK), "
        "or claude + model=haiku/sonnet as last-resort catch-all. Confirm only if none fit."
    ),
    "Explore": (
        "Explore returns uncompressed output. For pure locate tasks ('where is X', "
        "'what calls Y', 'map this dir') prefer caveman:cavecrew-investigator - compressed "
        "output, strictly cheaper. Confirm Explore only when scope is genuinely broad or "
        "analytical (investigator refuses analysis and its compressed output loses fidelity "
        "needed for deep comprehension tasks)."
    ),
}

def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    if input_data.get("tool_name") != "Agent":
        sys.exit(0)

    subagent_type = input_data.get("tool_input", {}).get("subagent_type", "")
    reason = NUDGES.get(subagent_type)
    if not reason:
        sys.exit(0)

    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(response))
    sys.exit(0)

if __name__ == "__main__":
    main()
