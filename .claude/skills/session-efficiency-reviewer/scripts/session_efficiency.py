#!/usr/bin/env python3
"""Privacy-preserving, deterministic linter for Claude Code JSONL sessions."""

from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable


DEFAULT_TRANSCRIPT_ROOT = Path.home() / ".claude" / "projects"
DIRECT_READ_TOOLS = {"Read"}
REPO_SEARCH_TOOLS = {"Glob", "Grep", "Read"}
MUTATING_TOOLS = {"Edit", "MultiEdit", "NotebookEdit", "Write"}
SEARCH_COMMAND = re.compile(
    r"(?:^|[;&|]\s*)(?:fd|find|grep|head|ls|pwd|rg|sed|stat|tail|tree|wc)\b"
    r"|(?:^|[;&|]\s*)git\s+(?:diff|log|ls-files|rev-parse|show|status)\b",
    re.IGNORECASE,
)
MUTATING_COMMAND = re.compile(
    r"(?:^|[;&|]\s*)(?:chmod|cp|install|mkdir|mv|rm|touch|truncate)\b"
    r"|(?:^|[;&|]\s*)git\s+(?:add|commit|merge|push|rebase|reset|switch)\b"
    r"|(?:^|[^<])(?:>>?|\btee\b)",
    re.IGNORECASE,
)


class Thresholds:
    def __init__(
        self,
        large_file_lines: int = 400,
        oversized_tool_bytes: int = 20_000,
        repeat_reads: int = 3,
        expensive_search_turns: int = 5,
        bash_calls: int = 6,
        large_skill_tokens: int = 8_000,
        skill_output_ratio: float = 0.10,
        chars_per_token: float = 4.0,
        high_context_tokens: int = 300_000,
        high_context_requests: int = 3,
        aggregate_tool_bytes: int = 50_000,
        medium_tool_bytes: int = 5_000,
        medium_tool_results: int = 2,
        max_subagent_requests: int = 10,
        max_main_requests: int = 25,
        hook_retry_count: int = 2,
        slow_shunt_ms: int = 30_000,
        large_shunt_result_bytes: int = 6_000,
        continuation_calls: int = 2,
        tool_errors: int = 10,
    ) -> None:
        self.large_file_lines = large_file_lines
        self.oversized_tool_bytes = oversized_tool_bytes
        self.repeat_reads = repeat_reads
        self.expensive_search_turns = expensive_search_turns
        self.bash_calls = bash_calls
        self.large_skill_tokens = large_skill_tokens
        self.skill_output_ratio = skill_output_ratio
        self.chars_per_token = chars_per_token
        self.high_context_tokens = high_context_tokens
        self.high_context_requests = high_context_requests
        self.aggregate_tool_bytes = aggregate_tool_bytes
        self.medium_tool_bytes = medium_tool_bytes
        self.medium_tool_results = medium_tool_results
        self.max_subagent_requests = max_subagent_requests
        self.max_main_requests = max_main_requests
        self.hook_retry_count = hook_retry_count
        self.slow_shunt_ms = slow_shunt_ms
        self.large_shunt_result_bytes = large_shunt_result_bytes
        self.continuation_calls = continuation_calls
        self.tool_errors = tool_errors


def byte_size(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value.encode("utf-8", errors="replace"))
    try:
        rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        rendered = str(value)
    return len(rendered.encode("utf-8", errors="replace"))


def looks_structured(value: Any) -> bool:
    if isinstance(value, (dict, list)):
        return True
    if not isinstance(value, str):
        return False
    stripped = value.lstrip()
    if not stripped or stripped[0] not in "[{":
        return False
    try:
        json.loads(stripped)
    except (json.JSONDecodeError, RecursionError):
        return False
    return True


def estimated_tokens(size: int, thresholds: Thresholds) -> int:
    return math.ceil(size / thresholds.chars_per_token) if size else 0


def usage_value(usage: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = usage.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return max(value, 0)
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return 0


def usage_counters(usage: dict[str, Any]) -> dict[str, int]:
    cache_read = usage_value(usage, "cache_read_input_tokens", "cacheReadInputTokens")
    if not cache_read:
        details = usage.get("input_tokens_details") or usage.get("inputTokensDetails")
        if isinstance(details, dict):
            cache_read = usage_value(details, "cached_tokens", "cachedTokens")
    cache_creation = usage_value(
        usage, "cache_creation_input_tokens", "cacheCreationInputTokens"
    )
    if not cache_creation:
        creation = usage.get("cache_creation") or usage.get("cacheCreation")
        if isinstance(creation, dict):
            cache_creation = sum(
                value
                for key, value in creation.items()
                if isinstance(value, int)
                and not isinstance(value, bool)
                and (key.endswith("_input_tokens") or key.endswith("InputTokens"))
            )
    return {
        "input_tokens": usage_value(usage, "input_tokens", "inputTokens"),
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_creation,
    }


def safe_path(raw: Any, cwd: Path) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return "<unknown>"
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = cwd / candidate
    try:
        return candidate.resolve(strict=False).relative_to(cwd.resolve(strict=False)).as_posix()
    except (OSError, ValueError):
        return f"…/{candidate.name}" if candidate.name else "<external>"


def model_tier(model: Any) -> str | None:
    lowered = str(model or "").lower()
    for tier in ("haiku", "sonnet", "opus"):
        if tier in lowered:
            return tier
    return None


def normalized_agent_id(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return re.sub(r"^agent-", "", value.strip(), flags=re.IGNORECASE)


def safe_result_marker(content: Any) -> str | None:
    if not isinstance(content, str):
        return None
    lowered = content.lower()
    if "mandatory skill not loaded" in lowered or "required skill not loaded" in lowered:
        return "missing_skill"
    if "shunt bulk-reader delegation is still required" in lowered:
        return "shunt_pending_read"
    if "shunt code-writer delegation is still required" in lowered:
        return "shunt_pending_write"
    if (
        "read can expose more than" in lowered
        and "shunt.py read" in lowered
    ) or "shell read can expose more than" in lowered:
        return "shunt_read_denied"
    return None


def shunt_receipt(content: Any) -> dict[str, Any] | None:
    if not isinstance(content, str) or "SHUNT_RECEIPT " not in content:
        return None
    raw = content.split("SHUNT_RECEIPT ", 1)[1].splitlines()[0]
    try:
        receipt = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(receipt, dict):
        return None
    allowed = {
        key: receipt[key]
        for key in (
            "op",
            "files",
            "input_bytes",
            "result_bytes",
            "worker_result_bytes",
            "elapsed_ms",
            "truncated",
        )
        if key in receipt and isinstance(receipt[key], (str, int, bool))
    }
    return allowed or None


def project_key(project_root: Path) -> str:
    path = project_root.expanduser().resolve(strict=False).as_posix()
    return re.sub(r"[^A-Za-z0-9-]", "-", path)


def list_transcripts(
    project_root: Path,
    transcript_root: Path = DEFAULT_TRANSCRIPT_ROOT,
    limit: int = 5,
) -> list[Path]:
    project_dir = transcript_root.expanduser() / project_key(project_root)
    if not project_dir.is_dir():
        return []
    transcripts = [
        path
        for path in project_dir.glob("*.jsonl")
        if path.is_file() and has_model_activity(path)
    ]
    return sorted(transcripts, key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def has_model_activity(transcript: Path) -> bool:
    """Ignore shell-only session fragments such as a transcript created by /clear."""
    try:
        with transcript.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = event.get("message")
                if event.get("type") != "assistant" or not isinstance(message, dict):
                    continue
                if message.get("model") and isinstance(message.get("content"), list):
                    return True
    except OSError:
        return False
    return False


def transcript_touches(transcript: Path, target: Path, project_root: Path) -> bool:
    """Match an exact path mention without emitting transcript content."""
    expected = target.expanduser()
    if not expected.is_absolute():
        expected = project_root / expected
    expected = expected.resolve(strict=False)
    try:
        expected_relative = expected.relative_to(project_root.resolve(strict=False)).as_posix()
    except ValueError:
        expected_relative = ""
    needles = [str(expected)]
    if expected_relative:
        needles.append(expected_relative)
    for path in review_paths(transcript):
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if any(needle in line for needle in needles):
                    return True
    return False


def review_paths(transcript: Path, include_subagents: bool = True) -> list[Path]:
    transcript = transcript.expanduser().resolve(strict=False)
    paths = [transcript]
    if include_subagents:
        directory = transcript.parent / transcript.stem / "subagents"
        if directory.is_dir():
            paths.extend(sorted(path for path in directory.glob("*.jsonl") if path.is_file()))
    return paths


def _new_request(
    event: dict[str, Any], trace: int, turn: int, line_number: int
) -> dict[str, Any]:
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    usage = message.get("usage") if isinstance(message.get("usage"), dict) else {}
    counters = usage_counters(usage)
    return {
        "key": f"{trace}:{event.get('requestId') or event.get('uuid') or line_number}",
        "model": str(message.get("model") or "unknown"),
        "output_tokens": int(usage.get("output_tokens") or 0),
        **counters,
        "skill": event.get("attributionSkill"),
        "trace": trace,
        "turn": turn,
        "calls": [],
    }


def _apply_result(call: dict[str, Any], event: dict[str, Any], block: dict[str, Any]) -> None:
    content = block.get("content")
    call["result_bytes"] = byte_size(content)
    call["structured_result"] = looks_structured(content)
    call["result_error"] = bool(block.get("is_error"))
    call["result_marker"] = safe_result_marker(content)
    call["shunt_receipt"] = shunt_receipt(content)
    raw_result = event.get("toolUseResult")
    if not isinstance(raw_result, dict):
        return
    call["result_error"] = call["result_error"] or bool(raw_result.get("is_error"))
    if call["name"] == "Agent":
        call["agent_id"] = normalized_agent_id(raw_result.get("agentId"))
        if isinstance(raw_result.get("resolvedModel"), str):
            call["resolved_model"] = raw_result["resolvedModel"]
    file_meta = raw_result.get("file")
    if isinstance(file_meta, dict):
        for source, target in (
            ("totalLines", "total_lines"),
            ("numLines", "returned_lines"),
            ("startLine", "start_line"),
        ):
            value = file_meta.get(source)
            if isinstance(value, int) and not isinstance(value, bool):
                call[target] = value


def parse_transcripts(paths: Iterable[Path]) -> dict[str, Any]:
    paths = list(paths)
    calls: list[dict[str, Any]] = []
    call_by_id: dict[str, dict[str, Any]] = {}
    pending_results: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    requests: dict[str, dict[str, Any]] = {}
    invalid_lines = 0
    parsed_lines = 0
    trace_cwds: dict[int, Path] = {}
    trace_turns: collections.Counter[int] = collections.Counter()

    for trace, path in enumerate(paths):
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    event = json.loads(line)
                except (json.JSONDecodeError, RecursionError):
                    invalid_lines += 1
                    continue
                if not isinstance(event, dict):
                    invalid_lines += 1
                    continue
                parsed_lines += 1
                if isinstance(event.get("cwd"), str) and trace not in trace_cwds:
                    trace_cwds[trace] = Path(event["cwd"])
                message = event.get("message")
                if not isinstance(message, dict):
                    continue
                content = message.get("content")
                if event.get("type") == "user" and not event.get("isMeta"):
                    is_prompt = isinstance(content, str) and bool(content.strip())
                    if isinstance(content, list):
                        has_result = any(
                            isinstance(block, dict) and block.get("type") == "tool_result"
                            for block in content
                        )
                        has_text = any(
                            isinstance(block, dict)
                            and block.get("type") == "text"
                            and bool(str(block.get("text") or "").strip())
                            for block in content
                        )
                        is_prompt = has_text and not has_result
                    if is_prompt:
                        trace_turns[trace] += 1
                if not isinstance(content, list):
                    continue
                if event.get("type") == "assistant":
                    candidate = _new_request(event, trace, trace_turns[trace], line_number)
                    request = requests.setdefault(candidate["key"], candidate)
                    request["output_tokens"] = max(
                        request["output_tokens"], candidate["output_tokens"]
                    )
                    for counter in (
                        "input_tokens",
                        "cache_read_input_tokens",
                        "cache_creation_input_tokens",
                    ):
                        request[counter] = max(request[counter], candidate[counter])
                    if candidate["skill"]:
                        request["skill"] = candidate["skill"]
                    for block in content:
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        tool_input = block.get("input")
                        call = {
                            "id": str(block.get("id") or f"{candidate['key']}:{len(calls)}"),
                            "name": str(block.get("name") or "unknown"),
                            "input": tool_input if isinstance(tool_input, dict) else {},
                            "model": request["model"],
                            "request": candidate["key"],
                            "trace": trace,
                            "cwd": trace_cwds.get(trace, Path.cwd()),
                            "result_bytes": 0,
                            "structured_result": False,
                            "result_error": False,
                            "result_marker": None,
                            "shunt_receipt": None,
                        }
                        calls.append(call)
                        request["calls"].append(call)
                        call_by_id[call["id"]] = call
                        if call["id"] in pending_results:
                            result_event, result_block = pending_results.pop(call["id"])
                            _apply_result(call, result_event, result_block)
                elif event.get("type") == "user":
                    for block in content:
                        if not isinstance(block, dict) or block.get("type") != "tool_result":
                            continue
                        tool_id = str(block.get("tool_use_id") or "")
                        if tool_id in call_by_id:
                            _apply_result(call_by_id[tool_id], event, block)
                        elif tool_id:
                            pending_results[tool_id] = (event, block)
    return {
        "calls": calls,
        "requests": list(requests.values()),
        "invalid_lines": invalid_lines,
        "parsed_lines": parsed_lines,
        "trace_count": len(paths),
        "trace_stems": {index: path.stem for index, path in enumerate(paths)},
    }


def broad_read(call: dict[str, Any]) -> bool:
    tool_input = call["input"]
    return call["name"] in DIRECT_READ_TOOLS and not tool_input.get("offset") and not tool_input.get("limit")


def search_bash(call: dict[str, Any]) -> bool:
    if call["name"] != "Bash":
        return False
    command = call["input"].get("command")
    return (
        isinstance(command, str)
        and bool(SEARCH_COMMAND.search(command))
        and not bool(MUTATING_COMMAND.search(command))
    )


def repo_search_request(request: dict[str, Any]) -> bool:
    calls = request["calls"]
    if not calls:
        return False
    if any(call["name"] in MUTATING_TOOLS for call in calls):
        return False
    if any(call["name"] == "Bash" and not search_bash(call) for call in calls):
        return False
    return any(call["name"] in REPO_SEARCH_TOOLS or search_bash(call) for call in calls)


def validation_command_kind(call: dict[str, Any]) -> str | None:
    """Classify common local build/test commands without retaining command text."""
    if call["name"] != "Bash" or search_bash(call):
        return None
    command = str(call["input"].get("command") or "").lower()
    if not command:
        return None

    if re.search(r"(?:^|[;&|]\s*)(?:\./)?mvnw?\b", command):
        if not re.search(r"\b(?:compile|package|install|test|verify)\b", command):
            return None
        return "targeted" if any(
            selector in command for selector in ("-dtest=", "-dit.test=")
        ) else "broad"
    if re.search(r"(?:^|[;&|]\s*)(?:\./)?gradlew?\b", command):
        if not re.search(r"\b(?:assemble|build|check|test)\b", command):
            return None
        return "targeted" if "--tests" in command else "broad"
    if re.search(r"(?:^|[;&|]\s*)go\s+test\b", command):
        return "broad" if re.search(r"\./\.\.\.(?:\s|$)", command) else "targeted"
    if re.search(r"(?:^|[;&|]\s*)(?:python(?:3)?\s+-m\s+)?pytest\b", command):
        segment = re.split(r"[;&|]", command)[-1].strip()
        bare = re.fullmatch(
            r"(?:python(?:3)?\s+-m\s+)?pytest(?:\s+(?:-[a-z0-9-]+))*",
            segment,
        )
        return "broad" if bare else "targeted"
    if re.search(r"(?:^|[;&|]\s*)(?:npm|pnpm|yarn)\s+(?:run\s+)?test(?:\s|$)", command):
        return "broad"
    return None


def _skill_file(name: str, cwd: Path, roots: Iterable[Path]) -> Path | None:
    leaf = Path(name.split(":")[-1]).name
    if not leaf or leaf in {".", ".."}:
        return None
    candidates = [cwd / ".claude" / "skills", Path.home() / ".claude" / "skills"]
    candidates.extend(root.expanduser() for root in roots)
    for root in candidates:
        path = root / leaf / "SKILL.md"
        if path.is_file():
            return path
    return None


def warning(category: str, message: str, fix: str, **evidence: Any) -> dict[str, Any]:
    return {"category": category, "message": message, "evidence": evidence, "fix": fix}


def resolved_models_by_trace(parsed: dict[str, Any]) -> dict[int, str]:
    trace_by_agent = {
        normalized_agent_id(stem): trace
        for trace, stem in parsed["trace_stems"].items()
        if stem.lower().startswith("agent-")
    }
    resolved = {}
    for call in parsed["calls"]:
        if call["name"] != "Agent" or not call.get("resolved_model"):
            continue
        trace = trace_by_agent.get(call.get("agent_id"))
        if trace is not None:
            resolved[trace] = call["resolved_model"]
    return resolved


def effective_request_model(request: dict[str, Any], resolved: dict[int, str]) -> str:
    return resolved.get(request["trace"], request["model"])


def agent_model_mismatch(parsed: dict[str, Any]) -> dict[str, Any] | None:
    agent_calls = [
        call
        for call in parsed["calls"]
        if call["name"] == "Agent" and model_tier(call["input"].get("model"))
    ]
    child_tiers: dict[int, str] = {}
    for trace, stem in parsed["trace_stems"].items():
        if not stem.lower().startswith("agent-"):
            continue
        tiers = collections.Counter(
            tier
            for request in parsed["requests"]
            if request["trace"] == trace
            if (tier := model_tier(request["model"]))
        )
        if tiers:
            child_tiers[trace] = tiers.most_common(1)[0][0]
    if not agent_calls:
        return None

    trace_by_agent = {
        normalized_agent_id(parsed["trace_stems"][trace]): trace for trace in child_tiers
    }
    exact_call_indexes: set[int] = set()
    exact_traces: set[int] = set()
    exact_mismatches = 0
    requested = collections.Counter()
    recorded = collections.Counter()
    for index, call in enumerate(agent_calls):
        requested_tier = model_tier(call["input"].get("model"))
        resolved_tier = model_tier(call.get("resolved_model"))
        if resolved_tier:
            exact_call_indexes.add(index)
            requested[requested_tier] += 1
            recorded[resolved_tier] += 1
            if requested_tier != resolved_tier:
                exact_mismatches += 1
            trace = trace_by_agent.get(call.get("agent_id"))
            if trace is not None:
                exact_traces.add(trace)
            continue
        trace = trace_by_agent.get(call.get("agent_id"))
        if trace is None:
            continue
        actual_tier = child_tiers[trace]
        exact_call_indexes.add(index)
        exact_traces.add(trace)
        requested[requested_tier] += 1
        recorded[actual_tier] += 1
        if requested_tier != actual_tier:
            exact_mismatches += 1

    unmatched_requested = collections.Counter(
        model_tier(call["input"].get("model"))
        for index, call in enumerate(agent_calls)
        if index not in exact_call_indexes
    )
    unmatched_recorded = collections.Counter(
        tier for trace, tier in child_tiers.items() if trace not in exact_traces
    )
    requested.update(unmatched_requested)
    recorded.update(unmatched_recorded)
    heuristic_pairs = min(sum(unmatched_requested.values()), sum(unmatched_recorded.values()))
    heuristic_matches = sum(
        min(unmatched_requested[tier], unmatched_recorded[tier])
        for tier in ("haiku", "sonnet", "opus")
    )
    heuristic_mismatches = max(heuristic_pairs - heuristic_matches, 0)
    mismatches = exact_mismatches + heuristic_mismatches
    if not mismatches:
        return None
    association = "heuristic" if heuristic_pairs else "resolvedModel"
    return warning(
        "agent_model_mismatch",
        f"{mismatches} Agent call(s) resolved to a different model tier than requested",
        "Audit the Agent-to-runtime model handoff; treat toolUseResult.resolvedModel as authoritative when present.",
        mismatches=mismatches,
        requested_tiers=dict(sorted(requested.items())),
        resolved_runtime_tiers=dict(sorted(recorded.items())),
        association=association,
    )


def repeated_read_calls(path_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    successful = [
        call
        for call in path_calls
        if not call.get("result_error") and call.get("result_bytes", 0) > 0
    ]
    involved: set[int] = set()
    ranges = []
    for index, call in enumerate(successful):
        tool_input = call["input"]
        start = tool_input.get("offset") or call.get("start_line") or 1
        limit = tool_input.get("limit") or call.get("returned_lines")
        end = start + limit - 1 if isinstance(start, int) and isinstance(limit, int) else None
        ranges.append((start, end))
        for earlier, (old_start, old_end) in enumerate(ranges[:-1]):
            if end is None and old_end is None:
                involved.update((earlier, index))
                continue
            if end is None or old_end is None:
                continue
            overlap = max(0, min(end, old_end) - max(start, old_start) + 1)
            shorter = min(end - start + 1, old_end - old_start + 1)
            if shorter and overlap / shorter >= 0.8:
                involved.update((earlier, index))
    return [successful[index] for index in sorted(involved)]


def analyze(
    parsed: dict[str, Any],
    thresholds: Thresholds | None = None,
    skill_roots: Iterable[Path] = (),
) -> dict[str, Any]:
    thresholds = thresholds or Thresholds()
    calls = parsed["calls"]
    requests = parsed["requests"]
    warnings: list[dict[str, Any]] = []
    resolved_models = resolved_models_by_trace(parsed)

    reads: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for call in calls:
        if call["name"] == "Read":
            path = safe_path(call["input"].get("file_path"), call["cwd"])
            reads[path].append(call)

    large = {
        path: matching
        for path, path_calls in reads.items()
        if (
            matching := [
                call
                for call in path_calls
                if broad_read(call)
                and not call.get("result_error")
                and call.get("result_bytes", 0) > 0
                and (
                    call.get("total_lines", 0) > thresholds.large_file_lines
                    or call.get("result_bytes", 0) >= thresholds.oversized_tool_bytes
                )
            ]
        )
    }
    if large:
        size = sum(call["result_bytes"] for matches in large.values() for call in matches)
        item = warning(
            "large_direct_reads",
            (
                f"{len(large)} file(s) over {thresholds.large_file_lines:,} lines or "
                f"{thresholds.oversized_tool_bytes / 1000:.0f} KB were read directly"
            ),
            "Route bounded discovery through a Haiku explorer, use rg/jq with source-side limits, and verify only targeted line ranges in the parent.",
            files=sorted(large)[:10],
            estimated_avoidable_tokens=estimated_tokens(size, thresholds),
        )
        warnings.append(item)

    for path, path_calls in sorted(reads.items()):
        repeated = repeated_read_calls(path_calls)
        if len(repeated) < thresholds.repeat_reads:
            continue
        repeated_bytes = sum(call["result_bytes"] for call in repeated[1:])
        warnings.append(
            warning(
                "repeated_file_read",
                f"{path} had {len(repeated)} successful broad or substantially overlapping reads",
                "Reuse the earlier result or make one non-overlapping targeted follow-up read.",
                file=path,
                reads=len(repeated),
                estimated_avoidable_tokens=estimated_tokens(repeated_bytes, thresholds),
            )
        )

    expensive = [
        request
        for request in requests
        if model_tier(effective_request_model(request, resolved_models)) in {"sonnet", "opus"}
        and repo_search_request(request)
    ]
    if len(expensive) >= thresholds.expensive_search_turns:
        warnings.append(
            warning(
                "expensive_model_repo_search",
                f"Sonnet/Opus spent {len(expensive)} request(s) on repository search",
                "Use a bounded Haiku explorer or data-reader for discovery; keep the stronger model for decomposition and evaluation.",
                requests=len(expensive),
                models=sorted(
                    {effective_request_model(request, resolved_models) for request in expensive}
                ),
                heuristic=True,
            )
        )

    mismatch = agent_model_mismatch(parsed)
    if mismatch:
        warnings.append(mismatch)

    verifier_calls = [
        call
        for call in calls
        if call["name"] == "Agent"
        and str(call["input"].get("subagent_type") or "").lower() == "verifier"
    ]
    if verifier_calls:
        warnings.append(
            warning(
                "dedicated_verifier",
                f"{len(verifier_calls)} dedicated verifier agent(s) duplicated task checking",
                "Let CI own runtime verification, or let the implementation worker run one explicitly approved targeted Local check.",
                calls=len(verifier_calls),
            )
        )

    continuation_calls = [call for call in calls if call["name"] == "SendMessage"]
    if len(continuation_calls) >= thresholds.continuation_calls:
        warnings.append(
            warning(
                "subagent_continuation_churn",
                f"Workers received {len(continuation_calls)} continuation message(s)",
                "Dispatch one self-contained task without a turn cap; halt or issue a fresh narrower task when it cannot finish.",
                calls=len(continuation_calls),
            )
        )

    validation_kinds = collections.Counter(
        kind for call in calls if (kind := validation_command_kind(call))
    )
    if validation_kinds["broad"] > 1:
        warnings.append(
            warning(
                "repeated_broad_verification",
                f"The session attempted {validation_kinds['broad']} broad build/test commands",
                "Reserve at most one full suite for the final pre-MR state, or leave it to CI; use targeted checks during implementation.",
                calls=validation_kinds["broad"],
            )
        )

    tool_errors = sum(bool(call.get("result_error")) for call in calls)
    if tool_errors >= thresholds.tool_errors:
        warnings.append(
            warning(
                "tool_error_churn",
                f"Tool calls produced {tool_errors} error result(s)",
                "Correct the dispatch or hook contract after the first repeated failure; do not retry unchanged work.",
                calls=tool_errors,
            )
        )

    high_tier_turns: dict[tuple[int, int], list[dict[str, Any]]] = collections.defaultdict(list)
    for request in requests:
        if model_tier(effective_request_model(request, resolved_models)) in {"sonnet", "opus"}:
            high_tier_turns[(request["trace"], request["turn"])].append(request)
    high_context_turns = []
    for key, turn_requests in high_tier_turns.items():
        context_tokens = sum(
            request["input_tokens"]
            + request["cache_read_input_tokens"]
            + request["cache_creation_input_tokens"]
            for request in turn_requests
        )
        if (
            len(turn_requests) >= thresholds.high_context_requests
            and context_tokens >= thresholds.high_context_tokens
        ):
            high_context_turns.append((context_tokens, key, turn_requests))
    ranked_turns = sorted(
        high_context_turns,
        key=lambda item: (
            sum(len(request["calls"]) for request in item[2]) <= 3,
            item[0],
        ),
        reverse=True,
    )
    for context_tokens, (trace, turn), high_context in ranked_turns[:5]:
        cache_read = sum(request["cache_read_input_tokens"] for request in high_context)
        cache_creation = sum(request["cache_creation_input_tokens"] for request in high_context)
        direct_input = sum(request["input_tokens"] for request in high_context)
        tool_calls = sum(len(request["calls"]) for request in high_context)
        bounded = "bounded " if tool_calls <= 3 else ""
        warnings.append(
            warning(
                "high_context_replay",
                f"A {bounded}turn repeated {len(high_context)} Sonnet/Opus requests with {cache_read:,} cache-read input tokens",
                "Compact before bounded follow-up work or move it to a fresh, cheaper worker with only the required context.",
                requests=len(high_context),
                models=sorted(
                    {effective_request_model(request, resolved_models) for request in high_context}
                ),
                trace=trace + 1,
                turn=turn,
                tool_calls=tool_calls,
                input_tokens=direct_input,
                cache_read_input_tokens=cache_read,
                cache_creation_input_tokens=cache_creation,
                context_input_tokens=context_tokens,
            )
        )

    for call in calls:
        if call["name"] == "Read" or call["result_bytes"] < thresholds.oversized_tool_bytes:
            continue
        size = call["result_bytes"]
        kind = "structured" if call["structured_result"] else "text"
        warnings.append(
            warning(
                "oversized_tool_payload",
                f"{call['name']} returned a {size / 1000:.1f} KB {kind} payload",
                "Add a compact CLI wrapper or server-side projection so only required fields enter context.",
                tool=call["name"],
                bytes=size,
                estimated_context_tokens=estimated_tokens(size, thresholds),
            )
        )

    total_result_bytes = sum(call["result_bytes"] for call in calls)
    medium_results = sum(
        call["result_bytes"] >= thresholds.medium_tool_bytes for call in calls
    )
    if (
        total_result_bytes >= thresholds.aggregate_tool_bytes
        and medium_results >= thresholds.medium_tool_results
    ):
        warnings.append(
            warning(
                "aggregate_tool_output",
                f"Tool calls returned {total_result_bytes / 1000:.1f} KB across {medium_results} medium-or-larger results",
                "Batch related inspection and project or summarise output before it enters the parent context.",
                result_bytes=total_result_bytes,
                results_at_least_threshold=medium_results,
                result_threshold_bytes=thresholds.medium_tool_bytes,
                estimated_context_tokens=estimated_tokens(total_result_bytes, thresholds),
            )
        )

    requests_by_trace = collections.Counter(request["trace"] for request in requests)
    main_requests = requests_by_trace.get(0, 0)
    if main_requests > thresholds.max_main_requests:
        warnings.append(
            warning(
                "excessive_main_requests",
                f"Main trace made {main_requests} model requests (reference: {thresholds.max_main_requests})",
                "Narrow the dispatch, provide the required evidence up front, and stop or issue a fresh scoped task when it cannot finish.",
                trace=1,
                requests=main_requests,
                reference=thresholds.max_main_requests,
            )
        )
    long_subagents = [
        count
        for trace, count in requests_by_trace.items()
        if trace != 0 and count > thresholds.max_subagent_requests
    ]
    if long_subagents:
        warnings.append(
            warning(
                "unbounded_subagent",
                f"{len(long_subagents)} subagent trace(s) exceeded {thresholds.max_subagent_requests} model requests",
                "Narrow each dispatch and provide the required evidence up front; do not add turn caps or continuation messages.",
                traces=len(long_subagents),
                requests=sum(long_subagents),
                max_requests=max(long_subagents),
                reference=thresholds.max_subagent_requests,
            )
        )

    marker_counts = collections.Counter(
        call["result_marker"] for call in calls if call.get("result_marker")
    )
    for marker, count in sorted(marker_counts.items()):
        if marker == "shunt_read_denied":
            continue
        if count < thresholds.hook_retry_count:
            continue
        warnings.append(
            warning(
                "hook_retry_loop",
                f"Hook feedback {marker} caused {count} tool errors or retries",
                "Make the guard advisory or stateless, and never block Stop while recovery is pending.",
                marker=marker,
                occurrences=count,
            )
        )

    receipts = [call["shunt_receipt"] for call in calls if call.get("shunt_receipt")]
    slow_receipts = []
    large_receipts = []
    for receipt in receipts:
        if int(receipt.get("elapsed_ms") or 0) > thresholds.slow_shunt_ms:
            slow_receipts.append(receipt)
        if int(receipt.get("result_bytes") or 0) > thresholds.large_shunt_result_bytes:
            large_receipts.append(receipt)
    if slow_receipts or large_receipts:
        warnings.append(
            warning(
                "inefficient_shunt_worker",
                f"Shunt had {len(slow_receipts)} slow call(s) and {len(large_receipts)} oversized result(s)",
                "Keep the one-shot question narrow, cap returned bytes, and split inputs when latency remains high.",
                slow_calls=len(slow_receipts),
                oversized_results=len(large_receipts),
                slow_threshold_ms=thresholds.slow_shunt_ms,
                result_threshold_bytes=thresholds.large_shunt_result_bytes,
            )
        )

    shunt_operations = collections.Counter(
        str(receipt.get("op") or "unknown") for receipt in receipts
    )
    shunt_denials = marker_counts["shunt_read_denied"]
    if shunt_denials and not shunt_operations["read"]:
        warnings.append(
            warning(
                "shunt_bypassed_after_denial",
                f"Shunt rejected {shunt_denials} oversized read(s), but no bulk-reader call completed",
                "The removed Shunt route was bypassed; use one bounded Haiku explorer with rg/jq and source-side limits instead of reconstructing the file.",
                calls=shunt_denials,
            )
        )

    longest_bash_run: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    for call in calls:
        if search_bash(call) and (not current or current[-1]["trace"] == call["trace"]):
            current.append(call)
            if len(current) > len(longest_bash_run):
                longest_bash_run = list(current)
        else:
            current = []
    if len(longest_bash_run) >= thresholds.bash_calls:
        warnings.append(
            warning(
                "chatty_bash",
                f"{len(longest_bash_run)} consecutive repository-inspection Bash calls were made",
                "Batch independent inspections in one script or parallel tool batch and return one compact summary.",
                calls=len(longest_bash_run),
            )
        )

    skill_calls = collections.Counter(
        str(call["input"].get("skill"))
        for call in calls
        if call["name"] == "Skill" and call["input"].get("skill")
    )
    skill_output = collections.Counter()
    for request in requests:
        if request["skill"]:
            skill_output[str(request["skill"])] += request["output_tokens"]
    cwd = calls[0]["cwd"] if calls else Path.cwd()
    for name, invocations in skill_calls.items():
        path = _skill_file(name, cwd, skill_roots)
        if not path:
            continue
        injected = estimated_tokens(path.stat().st_size * invocations, thresholds)
        output = skill_output[name]
        if injected < thresholds.large_skill_tokens:
            continue
        if output > injected * thresholds.skill_output_ratio:
            continue
        warnings.append(
            warning(
                "oversized_underused_skill",
                f"Skill {name} injected about {injected:,} tokens with {output:,} attributed output tokens",
                "Move optional material into focused references and load only the branch needed for the request.",
                skill=name,
                invocations=invocations,
                estimated_injected_tokens=injected,
                attributed_output_tokens=output,
                output_is_usage_proxy=True,
            )
        )

    models = collections.Counter(
        effective_request_model(request, resolved_models) for request in requests
    )
    tools = collections.Counter(call["name"] for call in calls)
    input_tokens = sum(request["input_tokens"] for request in requests)
    cache_read = sum(request["cache_read_input_tokens"] for request in requests)
    cache_creation = sum(request["cache_creation_input_tokens"] for request in requests)
    return {
        "summary": {
            "traces": parsed["trace_count"],
            "parsed_lines": parsed["parsed_lines"],
            "invalid_lines": parsed["invalid_lines"],
            "model_requests": len(requests),
            "tool_calls": len(calls),
            "result_bytes": sum(call["result_bytes"] for call in calls),
            "input_tokens": input_tokens,
            "cache_read_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_creation,
            "context_input_tokens": input_tokens + cache_read + cache_creation,
            "models": dict(sorted(models.items())),
            "tools": dict(sorted(tools.items())),
            "skills": dict(sorted(skill_calls.items())),
            "tool_errors": tool_errors,
            "verification_commands": {
                "broad": validation_kinds["broad"],
                "targeted": validation_kinds["targeted"],
            },
            "shunt": {
                "read": shunt_operations["read"],
                "write": shunt_operations["write"],
                "denied_reads": shunt_denials,
            },
        },
        "warnings": warnings,
    }


def render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "Session efficiency review",
        (
            f"{len(report['warnings'])} warning(s); {summary['model_requests']} model request(s); "
            f"{summary['tool_calls']} tool call(s); {summary['traces']} trace(s)"
        ),
        (
            f"context/input/cache tokens: {summary['input_tokens']:,} input; "
            f"{summary['cache_read_input_tokens']:,} cache-read; "
            f"{summary['cache_creation_input_tokens']:,} cache-create"
        ),
        "models: "
        + ", ".join(f"{name}={count}" for name, count in summary["models"].items()),
        (
            f"verification commands: {summary['verification_commands']['targeted']} targeted; "
            f"{summary['verification_commands']['broad']} broad; "
            f"tool errors: {summary['tool_errors']}"
        ),
        (
            f"shunt: {summary['shunt']['read']} read; {summary['shunt']['write']} write; "
            f"{summary['shunt']['denied_reads']} denied oversized read"
        ),
    ]
    if summary["invalid_lines"]:
        lines.append(f"Skipped malformed/unsupported JSONL lines: {summary['invalid_lines']}")
    for item in report["warnings"]:
        lines.extend(("", f"⚠️  {item['message']}"))
        evidence = item["evidence"]
        for key in (
            "estimated_avoidable_tokens",
            "estimated_context_tokens",
            "requests",
            "calls",
            "traces",
            "max_requests",
            "reference",
            "tool_calls",
            "input_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
            "context_input_tokens",
        ):
            if key in evidence:
                label = key.replace("_", " ")
                value = evidence[key]
                lines.append(f"   {label}: {value:,}" if isinstance(value, int) else f"   {label}: {value}")
        if "files" in evidence:
            lines.append(f"   files: {', '.join(evidence['files'])}")
        for key in ("requested_tiers", "resolved_runtime_tiers", "association"):
            if key in evidence:
                lines.append(f"   {key.replace('_', ' ')}: {evidence[key]}")
        lines.append(f"   fix: {item['fix']}")
    if not report["warnings"]:
        lines.append("No configured anti-pattern threshold was crossed.")
    return "\n".join(lines)


def add_review_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("transcript", nargs="?", type=Path)
    parser.add_argument("--latest", action="store_true", help="review the latest main transcript")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--transcript-root", type=Path, default=DEFAULT_TRANSCRIPT_ROOT)
    parser.add_argument("--skill-root", type=Path, action="append", default=[])
    parser.add_argument("--main-only", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--strict", action="store_true", help="exit 1 when warnings are found")
    parser.add_argument("--large-file-lines", type=int, default=400)
    parser.add_argument("--oversized-tool-bytes", type=int, default=20_000)
    parser.add_argument("--repeat-reads", type=int, default=3)
    parser.add_argument("--expensive-search-turns", type=int, default=5)
    parser.add_argument("--bash-calls", type=int, default=6)
    parser.add_argument("--large-skill-tokens", type=int, default=8_000)
    parser.add_argument("--skill-output-ratio", type=float, default=0.10)
    parser.add_argument("--chars-per-token", type=float, default=4.0)
    parser.add_argument("--high-context-tokens", type=int, default=300_000)
    parser.add_argument("--high-context-requests", type=int, default=3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="list recent main-session transcripts")
    listing.add_argument("--project-root", type=Path, default=Path.cwd())
    listing.add_argument("--transcript-root", type=Path, default=DEFAULT_TRANSCRIPT_ROOT)
    listing.add_argument("--limit", type=int, default=5)
    listing.add_argument(
        "--mentions-path",
        "--touches",
        dest="touches",
        type=Path,
        help="only sessions whose main or subagent trace mentions this exact path",
    )
    listing.add_argument("--json", action="store_true", dest="as_json")
    review = commands.add_parser("review", help="lint a session transcript")
    add_review_arguments(review)
    args = parser.parse_args(argv)

    if args.command == "list":
        project_dir = args.transcript_root.expanduser() / project_key(args.project_root)
        candidates = list_transcripts(
            args.project_root,
            args.transcript_root,
            len(list(project_dir.glob("*.jsonl"))) if project_dir.is_dir() else 0,
        )
        if args.touches:
            candidates = [
                path
                for path in candidates
                if transcript_touches(path, args.touches, args.project_root)
            ]
        paths = candidates[: max(args.limit, 0)]
        if args.as_json:
            items = [
                {"path": str(path), "bytes": path.stat().st_size, "mtime": path.stat().st_mtime}
                for path in paths
            ]
            print(json.dumps(items, indent=2, sort_keys=True))
        else:
            for path in paths:
                stat = path.stat()
                print(f"{int(stat.st_mtime)}\t{stat.st_size}\t{path}")
        return 0

    if args.transcript and args.latest:
        parser.error("pass a transcript or --latest, not both")
    transcript = args.transcript
    if transcript is None:
        latest = list_transcripts(args.project_root, args.transcript_root, 1)
        if not latest:
            parser.error("no transcript found for the project")
        transcript = latest[0]
    if not transcript.is_file():
        parser.error(f"transcript not found: {transcript}")
    thresholds = Thresholds(
        args.large_file_lines,
        args.oversized_tool_bytes,
        args.repeat_reads,
        args.expensive_search_turns,
        args.bash_calls,
        args.large_skill_tokens,
        args.skill_output_ratio,
        args.chars_per_token,
        args.high_context_tokens,
        args.high_context_requests,
    )
    if thresholds.chars_per_token <= 0:
        parser.error("--chars-per-token must be greater than zero")
    parsed = parse_transcripts(review_paths(transcript, not args.main_only))
    report = analyze(parsed, thresholds, args.skill_root)
    print(json.dumps(report, indent=2, sort_keys=True) if args.as_json else render_text(report))
    return 1 if args.strict and report["warnings"] else 0


if __name__ == "__main__":
    sys.exit(main())
