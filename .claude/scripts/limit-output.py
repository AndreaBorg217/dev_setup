#!/usr/bin/env python3
"""Cap unbounded reads so raw output never floods model context.

Grep/rg-first: a capped search beats a full read. Any Read/Bash/Grep/WebFetch
that would ingest >MAX_LINES or >MAX_BYTES without a cap, projection, or
sandbox filter is denied with one exact fix. WebSearch snippets are small
and pass; full page fetches must go through ctx_fetch_and_index + ctx_search.
"""

import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any

MAX_LINES = 500
MAX_BYTES = 20 * 1024
GREP_HEAD_LIMIT = 50

DUMP_TOOLS = {"cat", "bat", "less", "more"}
GREP_TOOLS = {"grep", "rg", "egrep", "fgrep"}
GREP_CAP_FLAGS = {
    "-l", "--files-with-matches", "--files", "-c", "--count",
    "-m", "--max-count",
}
LOG_TOOLS_RE = re.compile(r"\b(kubectl|argo|docker|docker-compose)\b[^|;&]*\blogs\b|\bjournalctl\b", re.IGNORECASE)
KUBECTL_GET_RE = re.compile(r"\bkubectl\b[^|;&]*\bget\b", re.IGNORECASE)
OUTPUT_FMT_RE = re.compile(r"-o\s*(yaml|json|jsonpath)|--output[=\s]*(yaml|json|jsonpath)", re.IGNORECASE)
NAMED_OUTPUT_RE = re.compile(r"-o\s*(name|custom-columns)|--output[=\s]*(name|custom-columns)", re.IGNORECASE)
SELECT_STAR_RE = re.compile(r"\bselect\s+\*", re.IGNORECASE)
LIMIT_RE = re.compile(r"\blimit\b", re.IGNORECASE)
CAP_SINK_RE = re.compile(r"\|\s*(head|jq|yq|rg|grep)\b|(-m\s*\d+|--max-count\s*\d+)", re.IGNORECASE)
TAIL_FLAG_RE = re.compile(r"(--tail[=\s]+\d+|--since\b|-n\s*\d+|--max-log-requests\b)", re.IGNORECASE)


def main() -> int:
    """Route the hook input to the matching checker; deny when it returns a reason."""
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print("limit-output: invalid hook input: %s" % error, file=sys.stderr)
        return 1

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    cwd = data.get("cwd") or os.getcwd()

    reason = ""
    if tool_name == "Bash":
        reason = check_bash(tool_input.get("command", ""), cwd)
    elif tool_name == "Read":
        reason = check_read(tool_input, cwd)
    elif tool_name == "Grep":
        reason = check_grep_tool(tool_input)
    elif tool_name == "WebFetch":
        reason = check_webfetch(tool_input)

    if reason:
        deny(reason)
    return 0


def check_read(tool_input: dict[str, Any], cwd: str) -> str:
    """Deny an unbounded Read of a file over the line/byte gate."""
    raw_path = tool_input.get("file_path", "") or tool_input.get("path", "")
    path = resolve_path(raw_path, cwd)
    if not path or not path.is_file():
        return ""
    limit = tool_input.get("limit", tool_input.get("head_limit", None))
    if limit is not None:
        try:
            if int(limit) <= MAX_LINES:
                return ""
        except (TypeError, ValueError):
            pass
    lines, size = measure(path)
    if lines > MAX_LINES or size > MAX_BYTES:
        lines_display = "%d+" % MAX_LINES if lines > MAX_LINES else str(lines)
        return (
            "LIMIT_GUARD: '%s' has %s lines (%s). "
            "Run a capped search first: rg -n '<pattern>' %s -m %d. "
            "Read only an exact range (offset/limit<=%d) or use "
            "ctx_execute_file with intent." % (
                display_path(path), lines_display, fmt_bytes(size),
                display_path(path), GREP_HEAD_LIMIT, MAX_LINES,
            )
        )
    return ""


def check_grep_tool(tool_input: dict[str, Any]) -> str:
    """Deny an unbounded Grep content search; files/count mode or a cap passes."""
    mode = str(tool_input.get("output_mode", "content")).lower()
    if mode in ("files_with_matches", "count", "files"):
        return ""
    limit = tool_input.get("head_limit", tool_input.get("limit", None))
    if limit is not None:
        try:
            if int(limit) <= GREP_HEAD_LIMIT:
                return ""
        except (TypeError, ValueError):
            pass
    return (
        "LIMIT_GUARD: unbounded content search. "
        "Search files_with_matches (or count) first, then content with "
        "head_limit=%d." % GREP_HEAD_LIMIT
    )


def check_webfetch(tool_input: dict[str, Any]) -> str:
    """Deny a full page fetch; an extraction prompt or ctx sandboxing passes."""
    prompt = (
        tool_input.get("prompt", "") or tool_input.get("extract", "")
        or tool_input.get("query", "")
    )
    if prompt and prompt.strip():
        return ""
    url = tool_input.get("url", "")
    return (
        "LIMIT_GUARD: unbounded page fetch%s. "
        "Route through explorer with ctx_fetch_and_index, then retrieve "
        "only relevant sections via ctx_search; return links plus "
        "requested facts, never the full page." % (
            " of '%s'" % url if url else ""
        )
    )


def check_bash(command: str, cwd: str) -> str:
    """Deny Bash commands that would dump unbounded output into context."""
    command = command.strip()
    if not command:
        return ""
    if SELECT_STAR_RE.search(command) and not LIMIT_RE.search(command):
        return (
            "LIMIT_GUARD: SELECT * without LIMIT. "
            "Project explicit columns with LIMIT 20 "
            "(e.g. FORMAT TabSeparated | head -n 20)."
        )
    if KUBECTL_GET_RE.search(command) and OUTPUT_FMT_RE.search(command):
        if not NAMED_OUTPUT_RE.search(command) and not CAP_SINK_RE.search(command):
            return (
                "LIMIT_GUARD: kubectl get -o yaml/json without projection. "
                "Use -o name first (or -o custom-columns), or pipe to "
                "yq/jq with head -n 50."
            )
    if LOG_TOOLS_RE.search(command) and not TAIL_FLAG_RE.search(command):
        return (
            "LIMIT_GUARD: unbounded log stream. "
            "Add --tail 50 --since 30m and narrow further if still large."
        )
    is_api_call = (
        (re.search(r"\bcurl\b", command, re.IGNORECASE) and "/api/" in command)
        or re.search(r"\bglab\b[^|;&]*\bapi\b", command, re.IGNORECASE)
    )
    if is_api_call and ">/dev/null" not in command:
        if "| jq" not in command and "| head" not in command:
            return (
                "LIMIT_GUARD: unbounded API response. "
                "Pipe through jq with a projection and head -n 50 "
                "(curl: jq -r with a [:20] cap and @tsv, add --max-time 15)."
            )
    if re.search(r"\bglab\b[^|;&]*\bci\b[^|;&]*\btrace\b", command, re.IGNORECASE):
        if "| head" not in command and "| tail" not in command:
            return (
                "LIMIT_GUARD: unbounded job log stream. "
                "Pipe through tail -n 100 (or head -n 100 for the failure head)."
            )
    if re.search(r"\bglab\b[^|;&]*\bmr\b[^|;&]*\bdiff\b", command, re.IGNORECASE):
        if not CAP_SINK_RE.search(command):
            return (
                "LIMIT_GUARD: unbounded MR diff. "
                "Pipe through head -n 100 or diffstat; per-file stats via "
                "git diff --stat."
            )
    if re.search(r"\bglab\b[^|;&]*\bmr\b[^|;&]*\bview\b", command, re.IGNORECASE):
        if re.search(r"--comments\b|--output\s+json\b", command) and not CAP_SINK_RE.search(command):
            return (
                "LIMIT_GUARD: unbounded MR thread dump. "
                "Pipe through head -n 100 or jq with a projection."
            )
    for segment in split_segments(command):
        tokens = tokens_of(segment)
        if not tokens:
            continue
        tool = Path(tokens[0]).name
        if tool in DUMP_TOOLS:
            target = first_path_arg(tokens[1:])
            path = resolve_path(target, cwd) if target else None
            if path and path.is_file():
                lines, size = measure(path)
                if (lines > MAX_LINES or size > MAX_BYTES) and not CAP_SINK_RE.search(command):
                    lines_display = "%d+" % MAX_LINES if lines > MAX_LINES else str(lines)
                    return (
                        "LIMIT_GUARD: '%s' has %s lines (%s). "
                        "Do not cat it: rg -n '<pattern>' %s -m %d, or "
                        "yq/jq projection piped to head -n 50." % (
                            display_path(path), lines_display, fmt_bytes(size),
                            display_path(path), GREP_HEAD_LIMIT,
                        )
                    )
        if tool in GREP_TOOLS:
            if has_grep_cap(tokens) or CAP_SINK_RE.search(command):
                continue
            return (
                "LIMIT_GUARD: unbounded grep/rg. "
                "Run rg -l '<pattern>' <scope> first, then "
                "rg -n '<pattern>' <file> -m %d | head -n %d." % (
                    GREP_HEAD_LIMIT, GREP_HEAD_LIMIT,
                )
            )
        if tool == "git" and len(tokens) > 1 and tokens[1] == "grep":
            if has_grep_cap(tokens[1:]) or CAP_SINK_RE.search(command):
                continue
            return (
                "LIMIT_GUARD: unbounded git grep. "
                "Run git grep -l '<pattern>' first, then "
                "git grep -n '<pattern>' -- <path> | head -n %d." % GREP_HEAD_LIMIT
            )
    return ""


def has_grep_cap(tokens: list[str]) -> bool:
    """Check whether an rg/grep invocation already caps its own output."""
    for token in tokens[1:]:
        if token in GREP_CAP_FLAGS:
            return True
        if token.startswith("-m") and len(token) > 2:
            return True
    return False


def measure(path: Path) -> tuple[int, int]:
    """Return (lines capped at MAX_LINES+1, bytes) without reading huge files fully."""
    try:
        size = path.stat().st_size
    except OSError:
        return 0, 0
    lines = 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for _ in handle:
                lines += 1
                if lines > MAX_LINES:
                    break
    except OSError:
        return 0, size
    return lines, size


def fmt_bytes(size: int) -> str:
    """Format a byte count for deny messages."""
    if size >= 1024:
        return "%d KB" % (size // 1024)
    return "%d B" % size


def split_segments(command: str) -> list[str]:
    """Split a shell command on pipes and sequencing operators, honouring quotes."""
    segments, current, quote, escaped = [], [], "", False
    i = 0
    while i < len(command):
        char = command[i]
        if escaped:
            current.append(char)
            escaped = False
            i += 1
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            i += 1
            continue
        if quote:
            current.append(char)
            if char == quote:
                quote = ""
            i += 1
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
            i += 1
            continue
        if command.startswith("&&", i) or command.startswith("||", i):
            text = "".join(current).strip()
            if text:
                segments.append(text)
            current = []
            i += 2
            continue
        if char in {"|", ";", "\n"}:
            text = "".join(current).strip()
            if text:
                segments.append(text)
            current = []
            i += 1
            continue
        current.append(char)
        i += 1
    text = "".join(current).strip()
    if text:
        segments.append(text)
    return segments


def tokens_of(segment: str) -> list[str]:
    """Split one pipeline segment into shell tokens, tolerating bad quoting."""
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def first_path_arg(args: list[str]) -> str:
    """Return the first non-option argument, honouring a `--` separator."""
    for index, arg in enumerate(args):
        if arg == "--":
            rest = args[index + 1:]
            return rest[0] if rest else ""
        if arg.startswith("-"):
            continue
        return arg
    return ""


def resolve_path(raw_path: str, cwd: str) -> Path | None:
    """Resolve a hook path argument against the session cwd; None when absent."""
    if not raw_path:
        return None
    raw_path = raw_path.strip().strip("'\"")
    if not raw_path or raw_path == "-":
        return None
    expanded = os.path.expanduser(os.path.expandvars(raw_path))
    path = Path(expanded)
    if not path.is_absolute():
        path = Path(cwd) / path
    return path.resolve(strict=False)


def display_path(path: Path) -> str:
    """Render a path with $HOME shortened for deny messages."""
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def deny(reason: str) -> None:
    """Emit the PreToolUse deny decision consumed by Claude Code."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


if __name__ == "__main__":
    raise SystemExit(main())
