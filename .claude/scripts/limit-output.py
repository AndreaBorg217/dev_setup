#!/usr/bin/env python3
"""Cap unbounded reads so raw output never floods model context.

Grep/rg-first: a capped search beats a full read. Any Read/Bash/Grep/WebFetch
that would ingest >MAX_LINES or >MAX_BYTES without a cap, projection, or
sandbox filter is denied with one exact fix. WebSearch snippets are small
and pass; full page fetches must go through ctx_fetch_and_index + ctx_search.
"""

import json
import glob as globmod
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any

MAX_LINES = 500
MAX_BYTES = 20 * 1024
GREP_HEAD_LIMIT = 50
# Managed config/docs are frequently read whole — exempt up to a higher
# soft cap so the hook guides rather than blocks legitimate re-opens.
MANAGED_EXEMPT_LINES = 1500
MANAGED_EXEMPT_BYTES = 100 * 1024

DUMP_TOOLS = {"cat", "bat", "less", "more"}
GREP_TOOLS = {"grep", "rg", "egrep", "fgrep"}
GREP_CAP_FLAGS = {
    "-l", "--files-with-matches", "--files", "-c", "--count",
    "-m", "--max-count",
}
WRAPPER_PREFIXES = {"sudo", "env", "command", "nice", "time", "doas"}
LOG_TOOLS_RE = re.compile(r"\b(kubectl|argo|docker|docker-compose)\b[^|;&]*\blogs\b|\bjournalctl\b", re.IGNORECASE)
KUBECTL_GET_RE = re.compile(r"\bkubectl\b[^|;&]*\bget\b", re.IGNORECASE)
OUTPUT_FMT_RE = re.compile(r"-o\s*(yaml|json|jsonpath)|--output[=\s]*(yaml|json|jsonpath)", re.IGNORECASE)
NAMED_OUTPUT_RE = re.compile(r"-o\s*(name|custom-columns)|--output[=\s]*(name|custom-columns)", re.IGNORECASE)
SELECT_STAR_RE = re.compile(r"\bselect\s+\*", re.IGNORECASE)
LIMIT_RE = re.compile(r"\blimit\b", re.IGNORECASE)
# Only a downstream `head -n <bounded>` is a real cap. Plain `jq`/`grep`/`yq`
# without a numeric bound is a filter, not a cap — see Finding #2.
CAP_SINK_HEAD_RE = re.compile(r"\|\s*head\b[^|]*-n\s*(\d+)", re.IGNORECASE)
CAP_SINK_GREP_M_RE = re.compile(r"(?:-m\s*(\d+)|--max-count[=\s]+(\d+))", re.IGNORECASE)
# Legacy broad sink kept only for statement-local checks that need a quick
# filter hint (e.g. glab mr diff pipe). Not used as sole proof of boundedness.
CAP_SINK_RE = re.compile(r"\|\s*(head|jq|yq|rg|grep)\b|(-m\s*\d+|--max-count\s*\d+)", re.IGNORECASE)
TAIL_FLAG_RE = re.compile(r"(--tail[=\s]+\d+|--since\b|-n\s*\d+|--max-log-requests\b)", re.IGNORECASE)
# Strict: only --tail / -n with a numeric value count as a real cap. --since
# alone is not bounded (Finding #5).
TAIL_CAP_RE = re.compile(r"(--tail[=\s]*(\d+)|-n\s*(\d+))", re.IGNORECASE)


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
        reason = check_grep_tool(tool_input, cwd)
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
            val = int(limit)
            if 1 <= val <= MAX_LINES:
                # Even with a line cap, enforce byte cap on the estimated slice.
                lines, size = measure(path)
                if lines and size:
                    est_bytes = int(size * min(val, lines) / lines) if lines else size
                    if est_bytes > MAX_BYTES:
                        if _is_managed_exempt(path) and est_bytes <= MANAGED_EXEMPT_BYTES:
                            return ""
                        return (
                            "LIMIT_GUARD: '%s' slice %d lines is ~%s (>%s). "
                            "Use a smaller limit or ctx_execute_file with intent." % (
                                display_path(path), val, fmt_bytes(est_bytes), fmt_bytes(MAX_BYTES),
                            )
                        )
                return ""
            if val <= 0 or val > MAX_LINES:
                return (
                    "LIMIT_GUARD: invalid limit %r — must be 1..%d." % (limit, MAX_LINES)
                )
        except (TypeError, ValueError):
            pass
    lines, size = measure(path)
    # Exempt managed config/docs re-opens (CLAUDE.md, managed .md/.json)
    # up to a higher soft cap — keeps the guardrail for huge logs/dumps.
    if _is_managed_exempt(path):
        if lines <= MANAGED_EXEMPT_LINES and size <= MANAGED_EXEMPT_BYTES:
            return ""
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


def _is_managed_exempt(path: Path) -> bool:
    """Managed config and prose docs are safe to re-open whole."""
    text = str(path)
    # dev_setup managed config
    if "/.claude/" in text:
        return True
    # Prose/docs that are intentionally read whole for style/contract
    if path.suffix.lower() in {".md", ".json", ".yml", ".yaml"}:
        # keep exemption bounded — huge files still go via sandbox
        return True
    return False


def check_grep_tool(tool_input: dict[str, Any], cwd: str = "") -> str:
    """Deny an unbounded Grep content search; files/count mode or a cap passes."""
    mode = str(tool_input.get("output_mode", "content")).lower()
    if mode in ("files_with_matches", "count", "files"):
        return ""
    limit = tool_input.get("head_limit", tool_input.get("limit", None))
    if limit is not None:
        try:
            if 1 <= int(limit) <= GREP_HEAD_LIMIT:
                return ""
            if int(limit) > GREP_HEAD_LIMIT:
                return (
                    "LIMIT_GUARD: head_limit %s exceeds max %d. Use %d or files_with_matches first." % (
                        limit, GREP_HEAD_LIMIT, GREP_HEAD_LIMIT,
                    )
                )
        except (TypeError, ValueError):
            pass
    # Validate explicit -m / --max-count on the pattern if present.
    for key in ("pattern", "query"):
        pat = tool_input.get(key, "")
        if isinstance(pat, str) and _grep_cap_exceeds(pat):
            return (
                "LIMIT_GUARD: grep -m/--max-count exceeds %d. Cap at %d." % (
                    GREP_HEAD_LIMIT, GREP_HEAD_LIMIT,
                )
            )
    # Single-file content searches are already bounded — allow without head_limit.
    raw_path = tool_input.get("path", "")
    if raw_path and cwd:
        candidate = resolve_path(raw_path, cwd)
        if candidate and candidate.is_file():
            return ""
        # Legacy callers without cwd: treat an explicit file-looking path as bounded.
        if isinstance(raw_path, str) and "." in Path(raw_path).name:
            return ""
    return (
        "LIMIT_GUARD: unbounded content search. "
        "Search files_with_matches (or count) first, then content with "
        "head_limit=%d." % GREP_HEAD_LIMIT
    )


def _grep_cap_exceeds(text: str) -> bool:
    """Return True if text contains -m/--max-count with value > GREP_HEAD_LIMIT."""
    for m in CAP_SINK_GREP_M_RE.finditer(text):
        val = m.group(1) or m.group(2)
        try:
            if int(val) > GREP_HEAD_LIMIT:
                return True
        except (TypeError, ValueError):
            continue
    return False


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
    # Statement-local checks — caps must be in the same statement, not elsewhere
    # in a `;`/`&&`/`||` chain (Finding #1 / GPT #1).
    for statement in split_statements(command):
        stmt = statement.strip()
        if not stmt:
            continue
        if SELECT_STAR_RE.search(stmt) and not LIMIT_RE.search(stmt):
            return (
                "LIMIT_GUARD: SELECT * without LIMIT. "
                "Project explicit columns with LIMIT 20 "
                "(e.g. FORMAT TabSeparated | head -n 20)."
            )
        if KUBECTL_GET_RE.search(stmt) and OUTPUT_FMT_RE.search(stmt):
            if not NAMED_OUTPUT_RE.search(stmt) and not _statement_has_cap(stmt):
                return (
                    "LIMIT_GUARD: kubectl get -o yaml/json without projection. "
                    "Use -o name first (or -o custom-columns), or pipe to "
                    "yq/jq with head -n 50."
                )
        if LOG_TOOLS_RE.search(stmt) and not _statement_has_log_cap(stmt):
            return (
                "LIMIT_GUARD: unbounded log stream. "
                "Add --tail 50 --since 30m and narrow further if still large."
            )
        # API call: whitespace-tolerant, case-insensitive /api/, tolerant sink check
        is_api_call = (
            (re.search(r"\bcurl\b", stmt, re.IGNORECASE) and re.search(r"/api/", stmt, re.IGNORECASE))
            or re.search(r"\bglab\b[^|;&]*\bapi\b", stmt, re.IGNORECASE)
        )
        if is_api_call and not re.search(r">\s*/dev/null", stmt):
            if not _statement_has_api_cap(stmt):
                return (
                    "LIMIT_GUARD: unbounded API response. "
                    "Pipe through jq with a projection and head -n 50 "
                    "(curl: jq -r with a [:20] cap and @tsv, add --max-time 15)."
                )
        if re.search(r"\bglab\b[^|;&]*\bci\b[^|;&]*\btrace\b", stmt, re.IGNORECASE):
            if not re.search(r"\|\s*(head|tail)\b", stmt, re.IGNORECASE):
                return (
                    "LIMIT_GUARD: unbounded job log stream. "
                    "Pipe through tail -n 100 (or head -n 100 for the failure head)."
                )
        if re.search(r"\bglab\b[^|;&]*\bmr\b[^|;&]*\bdiff\b", stmt, re.IGNORECASE):
            if not _statement_has_cap(stmt):
                return (
                    "LIMIT_GUARD: unbounded MR diff. "
                    "Pipe through head -n 100 or diffstat; per-file stats via "
                    "git diff --stat."
                )
        if re.search(r"\bglab\b[^|;&]*\bmr\b[^|;&]*\bview\b", stmt, re.IGNORECASE):
            if re.search(r"--comments\b|--output\s+json\b", stmt) and not _statement_has_cap(stmt):
                return (
                    "LIMIT_GUARD: unbounded MR thread dump. "
                    "Pipe through head -n 100 or jq with a projection."
                )
        # Pipeline-local dump/grep checks within this statement.
        pipelines = split_pipelines(stmt)
        for idx, segment in enumerate(pipelines):
            tokens = tokens_of(segment)
            if not tokens:
                continue
            tool = unwrap_wrapper(tokens)
            if not tool:
                continue
            tool_name = Path(tool).name
            # Check for redirection targets in this segment (cat < huge.log)
            redir_targets = find_redirect_targets(segment, cwd)
            if tool_name in DUMP_TOOLS:
                # Check positional file args — inspect every file, not just first.
                for target in file_args_for_dump(tokens):
                    path = resolve_path(target, cwd)
                    if path and path.is_file():
                        lines, size = measure(path)
                        if (lines > MAX_LINES or size > MAX_BYTES) and not _pipeline_has_cap(pipelines, idx):
                            lines_display = "%d+" % MAX_LINES if lines > MAX_LINES else str(lines)
                            return (
                                "LIMIT_GUARD: '%s' has %s lines (%s). "
                                "Do not cat it: rg -n '<pattern>' %s -m %d, or "
                                "yq/jq projection piped to head -n 50." % (
                                    display_path(path), lines_display, fmt_bytes(size),
                                    display_path(path), GREP_HEAD_LIMIT,
                                )
                            )
                    elif target and ("*" in target or "?" in target or "[" in target):
                        # Glob that didn't resolve — cannot verify boundedness.
                        if not _pipeline_has_cap(pipelines, idx):
                            return (
                                "LIMIT_GUARD: glob '%s' may expand to large files. "
                                "Narrow to a single file or pipe to head -n 50." % target
                            )
                # Redirection: cat < huge.log, cat <(process)
                for rpath in redir_targets:
                    lines, size = measure(rpath)
                    if (lines > MAX_LINES or size > MAX_BYTES) and not _pipeline_has_cap(pipelines, idx):
                        lines_display = "%d+" % MAX_LINES if lines > MAX_LINES else str(lines)
                        return (
                            "LIMIT_GUARD: redirect '%s' has %s lines (%s). "
                            "Do not cat it: rg -n '<pattern>' %s -m %d, or "
                            "yq/jq projection piped to head -n 50." % (
                                display_path(rpath), lines_display, fmt_bytes(size),
                                display_path(rpath), GREP_HEAD_LIMIT,
                            )
                        )
                # No file arg but has redirection or is bare cat with pipeline cap?
                if not file_args_for_dump(tokens) and not redir_targets:
                    # `cat` without file reads stdin — only allow if downstream caps.
                    pass
            if tool_name in GREP_TOOLS:
                if has_grep_cap(tokens) and _grep_cap_within_limit(tokens):
                    continue
                if _pipeline_has_bounded_cap(pipelines, idx):
                    continue
                return (
                    "LIMIT_GUARD: unbounded grep/rg. "
                    "Run rg -l '<pattern>' <scope> first, then "
                    "rg -n '<pattern>' <file> -m %d | head -n %d." % (
                        GREP_HEAD_LIMIT, GREP_HEAD_LIMIT,
                    )
                )
            if tool_name == "git" and len(tokens) > 1 and tokens[1] == "grep":
                if has_grep_cap(tokens[1:]) and _grep_cap_within_limit(tokens[1:]):
                    continue
                if _pipeline_has_bounded_cap(pipelines, idx):
                    continue
                return (
                    "LIMIT_GUARD: unbounded git grep. "
                    "Run git grep -l '<pattern>' first, then "
                    "git grep -n '<pattern>' -- <path> | head -n %d." % GREP_HEAD_LIMIT
                )
    return ""


def _statement_has_cap(stmt: str) -> bool:
    """Statement-local cap: downstream head with bounded -n or -m within limit."""
    if _has_bounded_head(stmt):
        return True
    m = CAP_SINK_GREP_M_RE.search(stmt)
    if m:
        val = m.group(1) or m.group(2)
        try:
            if int(val) <= GREP_HEAD_LIMIT:
                return True
        except (TypeError, ValueError):
            pass
    # Plain |jq / |yq without -n is not a cap (Finding #2) — ignore.
    return False


def _statement_has_log_cap(stmt: str) -> bool:
    """Log cap requires --tail or -n with numeric value, not --since alone."""
    m = TAIL_CAP_RE.search(stmt)
    if not m:
        return False
    # Extract numeric value and validate.
    for grp in m.groups():
        if grp and grp.isdigit():
            try:
                if int(grp) <= 500:
                    return True
            except ValueError:
                continue
    # If only --since without --tail/-n, not capped.
    return False


def _statement_has_api_cap(stmt: str) -> bool:
    """API cap is a downstream head/jq with filtering, or > /dev/null."""
    if re.search(r">\s*/dev/null", stmt):
        return True
    # Tolerant: | head, |head, | jq, |jq all count if bounded
    if _has_bounded_head(stmt):
        return True
    if re.search(r"\|\s*jq\b", stmt, re.IGNORECASE):
        # jq with head is bounded, bare jq is not — require head alongside.
        return bool(re.search(r"\|\s*head\b", stmt, re.IGNORECASE))
    if re.search(r"\|\s*head\b", stmt, re.IGNORECASE):
        return True
    return False


def _has_bounded_head(stmt: str) -> bool:
    """Return True if stmt pipes to head -n with value <= 200 (logs allow up to 200)."""
    for m in re.finditer(r"head\b[^|]*-n\s*(\d+)", stmt, re.IGNORECASE):
        try:
            if int(m.group(1)) <= 200:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _pipeline_has_cap(pipelines: list[str], idx: int) -> bool:
    """Check if pipeline from idx has any downstream cap sink."""
    downstream = " | ".join(pipelines[idx + 1 :])
    return _statement_has_cap(downstream)


def _pipeline_has_bounded_cap(pipelines: list[str], idx: int) -> bool:
    """Pipeline has a bounded cap downstream (head -n <= limit or -m <= limit)."""
    downstream = " | ".join(pipelines[idx + 1 :])
    if _has_bounded_head(downstream):
        return True
    for m in CAP_SINK_GREP_M_RE.finditer(downstream):
        val = m.group(1) or m.group(2)
        try:
            if int(val) <= GREP_HEAD_LIMIT:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _grep_cap_within_limit(tokens: list[str]) -> bool:
    """Check grep -m/--max-count value is within GREP_HEAD_LIMIT."""
    for i, tok in enumerate(tokens):
        if tok in ("-m", "--max-count") and i + 1 < len(tokens):
            try:
                if int(tokens[i + 1]) > GREP_HEAD_LIMIT:
                    return False
            except ValueError:
                return False
        elif tok.startswith("-m") and len(tok) > 2:
            try:
                if int(tok[2:]) > GREP_HEAD_LIMIT:
                    return False
            except ValueError:
                return False
        elif tok.startswith("--max-count="):
            try:
                if int(tok.split("=", 1)[1]) > GREP_HEAD_LIMIT:
                    return False
            except ValueError:
                return False
    return True


def has_grep_cap(tokens: list[str]) -> bool:
    """Check whether an rg/grep invocation already caps its own output."""
    for token in tokens[1:]:
        if token in GREP_CAP_FLAGS:
            return True
        if token.startswith("-m") and len(token) > 2:
            return True
    return False


def unwrap_wrapper(tokens: list[str]) -> str:
    """Strip wrapper prefixes (sudo, env, command) to find real tool."""
    idx = 0
    while idx < len(tokens) and tokens[idx] in WRAPPER_PREFIXES:
        idx += 1
        # env may have VAR=val assignments before tool
        while idx < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[idx]):
            idx += 1
    if idx < len(tokens):
        # Handle VAR=val prefix for time/nice etc.
        while idx < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[idx]):
            idx += 1
        if idx < len(tokens):
            return tokens[idx]
    return tokens[0] if tokens else ""


def file_args_for_dump(tokens: list[str]) -> list[str]:
    """Return all file args for cat/bat/less/more, skipping flags and values."""
    # Find real tool index after wrappers
    start = 0
    while start < len(tokens) and tokens[start] in WRAPPER_PREFIXES:
        start += 1
        while start < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[start]):
            start += 1
    # Skip VAR assignments
    while start < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[start]):
        start += 1
    if start >= len(tokens):
        return []
    args = tokens[start + 1 :]
    files: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            files.extend(args[i + 1 :])
            break
        if arg.startswith("-"):
            # Flags that take values: -n, --number etc for cat/bat — skip next
            if arg in ("-n", "--number"):
                i += 2
                continue
            # Unknown flag — skip
            i += 1
            continue
        if arg.startswith("+"):
            # more +10 file — skip +N
            if re.match(r"^\+\d+$", arg):
                i += 1
                continue
        files.append(arg)
        i += 1
    return files


def find_redirect_targets(segment: str, cwd: str) -> list[Path]:
    """Find < file and <(cmd) redirection targets in a segment."""
    targets: list[Path] = []
    # Simple < file (not << or <<<)
    for m in re.finditer(r"<\s*([^<>\s|&;]+)", segment):
        raw = m.group(1).strip().strip("'\"")
        if raw.startswith("("):
            continue
        path = resolve_path(raw, cwd)
        if path and path.is_file():
            targets.append(path)
        elif raw and ("*" not in raw and "?" not in raw):
            # Try glob resolution
            expanded = os.path.expanduser(os.path.expandvars(raw))
            p = Path(expanded)
            if not p.is_absolute():
                p = Path(cwd) / p
            for g in globmod.glob(str(p)):
                gp = Path(g)
                if gp.is_file():
                    targets.append(gp)
    return targets


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


def split_statements(command: str) -> list[str]:
    """Split on ; && || newline into independent statements, honouring quotes."""
    statements: list[str] = []
    current: list[str] = []
    quote = ""
    escaped = False
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
                statements.append(text)
            current = []
            i += 2
            continue
        if char in {";", "\n"}:
            text = "".join(current).strip()
            if text:
                statements.append(text)
            current = []
            i += 1
            continue
        current.append(char)
        i += 1
    text = "".join(current).strip()
    if text:
        statements.append(text)
    return statements


def split_pipelines(statement: str) -> list[str]:
    """Split a single statement on | into pipeline segments, honouring quotes."""
    segments: list[str] = []
    current: list[str] = []
    quote = ""
    escaped = False
    i = 0
    while i < len(statement):
        char = statement[i]
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
        if char == "|":
            # Avoid || already handled in split_statements — but if | remains, split.
            if statement.startswith("||", i):
                current.append(char)
                i += 1
                continue
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


def split_segments(command: str) -> list[str]:
    """Split a shell command on pipes and sequencing operators, honouring quotes."""
    # Kept for backwards compat — delegates to split_statements for now.
    # New code should use split_statements + split_pipelines.
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
        if arg.startswith("+") and re.match(r"^\+\d+$", arg):
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
