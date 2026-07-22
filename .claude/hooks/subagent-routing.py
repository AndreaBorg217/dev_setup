#!/usr/bin/env python3
"""PreToolUse hook that normalizes Agent routing before execution.

Ordinary routing corrections use ``updatedInput`` so Claude does not have to
spend another turn retrying the call. Opus (including the ``best`` alias) is
the only routing choice escalated to the user, and its model is never silently
downgraded.
"""

import json
import re
import sys


LOCATE_PATTERNS = [
    r"\b(where is|what calls|who calls|locate|search for|map (this )?(dir|directory))\b",
    r"\bfind\b.{0,40}\b(references?|usages?|callers?|definitions?|files?)\b",
    r"\b(search|scan)\b.{0,30}\b(codebase|repository|repo|files?|references?|usages?)\b",
    r"\bread (?:these )?files?\b",
]

ANALYSIS_PATTERNS = [
    r"\b(analy[sz]e|analysis|summari[sz]e|explain|triage|debug|design|compare|evaluate|infer)\b",
]

PLANNING_PATTERNS = [
    r"\b(create|draft|write|produce|make)\b.{0,30}\b(plan|proposal|spec|design doc|architecture)\b",
    r"\b(implementation plan|planning|roadmap|technical spec|design proposal)\b",
    r"\bplan\b.{0,30}\b(implementation|approach|work|changes?|feature|fix|steps?)\b",
]

IMPLEMENTATION_PATTERNS = [
    r"\b(implement|edit|modify|patch|refactor|fix|update|change)\b",
    r"\b(write|create|add)\b.{0,40}\b(code|file|test|component|function|class|module|endpoint|api)\b",
]

REVIEW_PATTERNS = [
    r"\b(review|code review|audit)\b",
    r"\binspect\b.{0,30}\b(diff|patch|changes?)\b",
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


def normalize_agent(subagent_type):
    if not isinstance(subagent_type, str):
        return ""
    return subagent_type.strip().lower()


def agent_role(subagent_type):
    """Return the unscoped agent name for built-in and plugin agents."""
    return normalize_agent(subagent_type).rsplit(":", maxsplit=1)[-1]


def text_blob(tool_input):
    parts = [
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


def is_opus_model(model):
    normalized = model_family(model)
    return normalized == "opus" or normalized == "best"


def is_pure_locate(text):
    conflicting_patterns = (
        ANALYSIS_PATTERNS
        + PLANNING_PATTERNS
        + IMPLEMENTATION_PATTERNS
        + REVIEW_PATTERNS
    )
    return matches_any(text, LOCATE_PATTERNS) and not matches_any(text, conflicting_patterns)


def routed_subagent(subagent_type, text):
    """Rewrite only agent selections with an unambiguous specialized target."""
    agent = normalize_agent(subagent_type)

    if agent == "general-purpose":
        if matches_any(text, PLANNING_PATTERNS):
            return "Plan"
        if matches_any(text, IMPLEMENTATION_PATTERNS):
            return "caveman:cavecrew-builder"
        if matches_any(text, REVIEW_PATTERNS):
            return "caveman:cavecrew-reviewer"
        if is_pure_locate(text):
            return "caveman:cavecrew-investigator"

    if agent == "explore" and is_pure_locate(text):
        return "caveman:cavecrew-investigator"

    return subagent_type


def expected_model(subagent_type, text):
    """Choose a model, giving an explicit agent role priority over keywords."""
    agent = normalize_agent(subagent_type)
    role = agent_role(subagent_type)

    if agent == "plan" or role == "cavecrew-builder":
        return "sonnet"

    if role in {"cavecrew-investigator", "cavecrew-reviewer"}:
        return "haiku"

    if agent in {"explore", "claude", "claude-code-guide", "general-purpose"}:
        return "haiku"

    if matches_any(text, PLANNING_PATTERNS + IMPLEMENTATION_PATTERNS):
        return "sonnet"

    if matches_any(text, HAIKU_PATTERNS):
        return "haiku"

    return "haiku"


def hook_output(decision, updated_input, reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
            # updatedInput replaces the complete object, so always return the
            # copied input rather than a patch containing only changed fields.
            "updatedInput": updated_input,
        }
    }


def evaluate(tool_input):
    """Return a hook response, or None when the Agent input is already valid."""
    original_agent = tool_input.get("subagent_type", "")
    original_agent = original_agent if isinstance(original_agent, str) else ""
    model = tool_input.get("model", "")
    text = text_blob(tool_input)

    updated_input = dict(tool_input)
    routed_agent = routed_subagent(original_agent, text)
    agent_changed = routed_agent != original_agent
    if agent_changed:
        updated_input["subagent_type"] = routed_agent

    if is_opus_model(model):
        return hook_output(
            "ask",
            updated_input,
            "Opus requires explicit user permission for this Agent call. "
            "The requested Opus model will be preserved if approved.",
        )

    expected = expected_model(routed_agent, text)
    model_changed = model_family(model) != expected
    if model_changed:
        updated_input["model"] = expected

    if not agent_changed and not model_changed:
        return None

    changes = []
    if agent_changed:
        changes.append(f"agent={routed_agent}")
    if model_changed:
        changes.append(f"model={expected}")

    return hook_output(
        "allow",
        updated_input,
        "Applied deterministic cost-aware Agent routing: " + ", ".join(changes) + ".",
    )


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception:
        return

    if input_data.get("tool_name") != "Agent":
        return

    tool_input = input_data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return

    response = evaluate(tool_input)
    if response is not None:
        print(json.dumps(response))


if __name__ == "__main__":
    main()
