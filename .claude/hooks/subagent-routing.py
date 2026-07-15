#!/usr/bin/env python3
"""
PreToolUse Hook: nudge Agent calls toward explicit, cheaper routing.

The hook asks instead of denying so the model can proceed when an exception is
intentional. It does not rewrite Agent input.
"""

import json
import re
import sys

GENERAL_PURPOSE_REASON = (
    "general-purpose is tools:* with uncompressed output - the biggest token "
    "sink among subagents. Prefer: caveman:cavecrew-investigator (locate code), "
    "caveman:cavecrew-builder (1-2 file edit), caveman:cavecrew-reviewer "
    "(diff review), Explore (broad analysis), Plan (planning), "
    "claude-code-guide (Claude Code/API/SDK), or claude with an explicit "
    "model=haiku/sonnet as last-resort catch-all. Confirm only if none fit."
)

EXPLORE_LOCATE_REASON = (
    "Explore returns uncompressed output. For pure locate/search tasks "
    "('where is X', 'what calls Y', 'map this dir'), prefer "
    "caveman:cavecrew-investigator with model=haiku. Confirm Explore only "
    "when the scope is genuinely broad or analytical."
)

LOCATE_PATTERNS = [
    r"\b(where is|what calls|who calls|locate|search for|map (this )?(dir|directory))\b",
    r"\bfind(?: all)? (?:references?|usages?|callers?|definitions?|files?)\b",
    r"\bread (?:these )?files?\b",
]

ANALYSIS_PATTERNS = [
    r"\b(analy[sz]e|analysis|summari[sz]e|explain|triage|debug|design|compare|evaluate|infer)\b",
]

PLANNING_PATTERNS = [
    r"\b(create|draft|write|produce|make)\b.{0,30}\b(plan|proposal|spec|design doc|architecture)\b",
    r"\b(implementation plan|planning|roadmap|technical spec|design proposal)\b",
]

IMPLEMENTATION_PATTERNS = [
    r"\b(implement|edit|modify|patch|refactor|fix|update|change)\b",
    r"\b(write|create|add)\b.{0,40}\b(code|file|test|component|function|class|module|endpoint|api)\b",
]

HAIKU_PATTERNS = [
    *LOCATE_PATTERNS,
    r"\b(test|tests|build|lint|typecheck|type-check|package manager|dependency|logs?|repro)\b",
    r"\b(fetch docs|read urls?|websearch|web search|current research|research)\b",
    r"\b(analy[sz]e|analysis|summari[sz]e|explain|triage|verify|verification)\b",
    r"\b(loop|loops|poll|polling|watch)\b",
]


def matches_any(text, patterns):
    return any(re.search(pattern, text) for pattern in patterns)


def text_blob(tool_input):
    parts = [
        tool_input.get("subagent_type", ""),
        tool_input.get("description", ""),
        tool_input.get("prompt", ""),
    ]
    return " ".join(part for part in parts if isinstance(part, str)).lower()


def model_family(model):
    if not isinstance(model, str):
        return ""

    normalized = model.strip().lower()
    for family in ("haiku", "sonnet", "opus"):
        if family in normalized:
            return family
    return normalized


def is_pure_locate(text):
    return matches_any(text, LOCATE_PATTERNS) and not matches_any(text, ANALYSIS_PATTERNS)


def expected_model(subagent_type, text):
    agent = subagent_type.lower()

    if agent == "plan" or matches_any(text, PLANNING_PATTERNS):
        return "opus", "Planning subagents should use model=opus."

    if "cavecrew-builder" in agent or matches_any(text, IMPLEMENTATION_PATTERNS):
        return "sonnet", "Implementation/edit subagents should use model=sonnet."

    if (
        agent == "claude"
        or "cavecrew-investigator" in agent
        or "cavecrew-reviewer" in agent
        or matches_any(text, HAIKU_PATTERNS)
    ):
        return "haiku", (
            "Search, read, noisy command, docs, research, triage, summarization, "
            "verification, loop, and polling subagents should use model=haiku."
        )

    return "haiku", "Default subagent model is haiku unless planning or implementation/editing."


def ask(reason):
    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(response))
    sys.exit(0)


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    if input_data.get("tool_name") != "Agent":
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        sys.exit(0)

    subagent_type = tool_input.get("subagent_type", "")
    subagent_type = subagent_type if isinstance(subagent_type, str) else ""
    model = tool_input.get("model", "")
    text = text_blob(tool_input)

    if subagent_type == "general-purpose":
        ask(GENERAL_PURPOSE_REASON)

    if subagent_type == "Explore" and is_pure_locate(text):
        ask(EXPLORE_LOCATE_REASON)

    expected, reason = expected_model(subagent_type, text)

    if not isinstance(model, str) or not model.strip():
        ask(
            "Set the Agent model parameter explicitly; do not inherit the "
            f"session model. Recommended: model={expected}. {reason}"
        )

    actual = model_family(model)
    if actual != expected:
        ask(
            f"Agent model appears mismatched: got model={model}, expected "
            f"model={expected}. {reason} Confirm only if this exception is intentional."
        )


if __name__ == "__main__":
    main()
