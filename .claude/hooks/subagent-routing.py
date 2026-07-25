#!/usr/bin/env python3
"""PreToolUse hook that normalizes Agent routing before execution.

This hook governs SUBAGENT delegation only (the ``Agent`` tool). It has no
effect on the main/top-level session model -- that is controlled entirely by
``settings.json``'s ``model`` field, ``/model``, or ``ANTHROPIC_MODEL``.

The only supported subagent model families are ``opus``, ``sonnet``, and
``haiku``. ``fable``, ``best``, and unknown model labels are never preserved.

Three tiers, clearly defined:

  OPUS   -- Planning and orchestration. Explicit or routed ``Plan`` calls use
            Opus, as do production-incident debugging/orchestration requests
            that need to coordinate Explore/log-search subagents. Custom
            agent/skill frontmatter may opt into ``opus``.

  SONNET -- Default execution tier. Implementation, review, ambiguous, and
            custom subagent calls land here unless a narrower rule applies.

  HAIKU  -- Search and command-runner tier. Explore/read-only locate work,
            active log/web search, URL fetches, tests, builds, dependency
            installs, checks, and curl/API probes use Haiku when delegated as
            standalone noisy execution tasks.
"""

import json
import re
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
CLAUDE_DIR = HOOKS_DIR.parent

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

LOG_OR_WEB_SEARCH_PATTERNS = [
    r"\b(search|scan|grep|query|inspect|read|fetch|tail|watch|poll|find)\b.{0,50}\b(logs?|log lines?|cloudwatch|datadog|splunk|loki|kibana|journalctl)\b",
    r"\b(logs?|log lines?|cloudwatch|datadog|splunk|loki|kibana|journalctl)\b.{0,50}\b(search|scan|grep|query|inspect|read|fetch|tail|watch|poll|find)\b",
    r"\b(websearch|web search|search the web|browse the web|webfetch|web fetch)\b",
    r"\b(fetch|read|open|search|research|look up|verify)\b.{0,50}\b(urls?|links?|web|internet|online|docs?|documentation|site|page)\b",
]

COMMAND_RUNNER_PATTERNS = [
    r"\b(run|execute|rerun|re-run|invoke|perform|start)\b.{0,50}\b(tests?|test suite|checks?|ci checks?|lint|typecheck|type-check|build|compile|dependency install|install dependencies|package install)\b",
    r"\b(run|execute|rerun|re-run|invoke|perform|start)\b.{0,50}\b(pytest|go test|cargo test|npm test|pnpm test|yarn test|bun test|vitest|jest|mocha)\b",
    r"\b(npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:test|build|lint|typecheck|type-check|check)\b",
    r"\b(npm|pnpm|yarn|bun)\s+(?:install|ci|update)\b",
    r"\b(pip3?|uv|poetry|bundle|gem|cargo|brew|apt(?:-get)?)\s+(?:install|update|add)\b",
    r"\b(cargo|go|mvn|mvnw|gradle|make|cmake)\s+(?:test|build|check|verify|compile)\b",
    r"\b(pytest|ruff|mypy|pyright|tsc|eslint|prettier|biome|vitest|jest|mocha)\b",
    r"\bdocker(?:\s+compose)?\s+build\b",
    r"\b(curl|httpie|wget)\b",
]

COMMAND_RUNNER_CONFLICT_PATTERNS = [
    r"\b(implement|edit|modify|patch|refactor|fix|update|change)\b",
    r"\b(debug|triage|investigate|diagnose|root cause|root-cause)\b",
    r"\b(review|code review|audit)\b",
    r"\b(plan|proposal|spec|design doc|architecture|roadmap)\b",
    r"\b(write|create|add)\b.{0,40}\b(code|file|test|component|function|class|module|endpoint|api)\b",
]

INCIDENT_ORCHESTRATION_PATTERNS = [
    r"\b(debug|triage|investigate|handle|coordinate|orchestrate|diagnose|respond to)\b.{0,70}\b(incident|outage|sev[ -]?[0-9]+|production issue|prod issue|service down|degradation|data loss)\b",
    r"\b(incident|outage|sev[ -]?[0-9]+|production issue|prod issue|service down|degradation|data loss)\b.{0,70}\b(debug|triage|investigate|handle|coordinate|orchestrate|diagnose|respond)\b",
]

MODEL_FAMILY_MARKERS = ("haiku", "sonnet", "opus", "fable", "best")
FRONTMATTER_OPT_IN_FAMILIES = {"opus"}


def matches_any(text, patterns):
    return any(re.search(pattern, text) for pattern in patterns)


def is_log_or_web_search(text):
    return matches_any(text, LOG_OR_WEB_SEARCH_PATTERNS)


def is_pure_command_runner(text):
    return matches_any(text, COMMAND_RUNNER_PATTERNS) and not matches_any(
        text, COMMAND_RUNNER_CONFLICT_PATTERNS
    )


def is_planning_orchestration(text):
    return matches_any(text, PLANNING_PATTERNS)


def is_incident_orchestration(text):
    return matches_any(text, INCIDENT_ORCHESTRATION_PATTERNS)


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
    for family in MODEL_FAMILY_MARKERS:
        if family in normalized:
            return family
    return normalized


def is_pure_locate(text):
    conflicting_patterns = (
        ANALYSIS_PATTERNS
        + PLANNING_PATTERNS
        + IMPLEMENTATION_PATTERNS
        + REVIEW_PATTERNS
    )
    return matches_any(text, LOCATE_PATTERNS) and not matches_any(
        text, conflicting_patterns
    )


def routed_subagent(subagent_type, text):
    """Rewrite only agent selections with an unambiguous specialized target."""
    agent = normalize_agent(subagent_type)

    if is_pure_command_runner(text):
        return subagent_type

    if agent == "general-purpose":
        if is_planning_orchestration(text) or is_incident_orchestration(text):
            return "Plan"
        if is_log_or_web_search(text):
            return "Explore"
        if matches_any(text, IMPLEMENTATION_PATTERNS):
            return "caveman:cavecrew-builder"
        if matches_any(text, REVIEW_PATTERNS):
            return "caveman:cavecrew-reviewer"
        if is_pure_locate(text):
            return "caveman:cavecrew-investigator"

    return subagent_type


def is_plan_agent(subagent_type):
    return agent_role(subagent_type) == "plan"


def subagent_frontmatter_model(subagent_type):
    role = agent_role(subagent_type)
    if not role:
        return ""

    candidate_paths = [
        CLAUDE_DIR / "agents" / f"{role}.md",
        CLAUDE_DIR / "skills" / role / "SKILL.md",
    ]
    candidate_paths.extend(CLAUDE_DIR.glob(f"plugins/marketplaces/*/agents/{role}.md"))
    candidate_paths.extend(
        CLAUDE_DIR.glob(f"plugins/marketplaces/*/plugins/*/agents/{role}.md")
    )
    candidate_paths.extend(
        CLAUDE_DIR.glob(f"plugins/marketplaces/*/skills/{role}/SKILL.md")
    )
    candidate_paths.extend(
        CLAUDE_DIR.glob(f"plugins/marketplaces/*/plugins/*/skills/{role}/SKILL.md")
    )

    for path in candidate_paths:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue

        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, flags=re.S)
        if not match:
            continue

        model_match = re.search(
            r"(?im)^\s*model\s*:\s*[\"']?([^\"'\n#]+)",
            match.group(1),
        )
        if model_match:
            return model_match.group(1).strip()

    return ""


def permitted_high_tier_family(original_agent):
    """Return the high-tier family this agent may use automatically.

    Returns ``"opus"`` for an explicit Plan agent, custom agent/skill
    frontmatter that opts into ``opus``, or ``None`` when no automatic
    high-tier grant applies.
    """
    if is_plan_agent(original_agent):
        return "opus"

    frontmatter_family = model_family(subagent_frontmatter_model(original_agent))
    if frontmatter_family in FRONTMATTER_OPT_IN_FAMILIES:
        return frontmatter_family

    return None


def expected_model(subagent_type, text, permitted_family=None):
    """Choose a model, giving an explicit agent role priority over keywords.

    Opus is reserved for orchestration, Sonnet is the default execution model,
    and Haiku is reserved for search. Unsupported families such as Fable are
    intentionally never returned.
    """
    agent = normalize_agent(subagent_type)
    role = agent_role(subagent_type)

    if is_pure_command_runner(text):
        return "haiku"

    if is_log_or_web_search(text):
        return "haiku"

    if permitted_family:
        return permitted_family

    if role == "plan":
        return "opus"

    if is_planning_orchestration(text) or is_incident_orchestration(text):
        return "opus"

    if role == "cavecrew-builder":
        return "sonnet"

    if role in {"cavecrew-investigator", "cavecrew-reviewer"}:
        if matches_any(text, LOCATE_PATTERNS):
            return "haiku"
        return "sonnet"

    if agent in {"explore", "claude", "claude-code-guide"}:
        return "haiku"

    if agent == "general-purpose":
        return "sonnet"

    if is_pure_locate(text):
        return "haiku"

    return "sonnet"


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

    permitted_family = permitted_high_tier_family(original_agent)
    expected = expected_model(routed_agent, text, permitted_family)

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
        "Applied deterministic Agent routing: " + ", ".join(changes) + ".",
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
