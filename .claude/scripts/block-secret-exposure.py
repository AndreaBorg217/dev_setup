#!/usr/bin/env python3
"""Block Claude tool calls that would expose plaintext secrets."""

import fnmatch
import json
import os
import re
import shlex
import sys
from pathlib import Path


SENSITIVE_FILE_GLOBS = [
    "~/.aws/**",
    "~/.azure/**",
    "~/.config/gcloud/**",
    "~/.config/gh/hosts.yml",
    "~/.git-credentials",
    "~/.kube/**",
    "~/.pgpass",
    "~/.ssh/**",
    "~/.terraform.d/credentials.tfrc.json",
    "~/.netrc",
    "**/.npmrc",
    "~/.docker/config.json",
    "**/.env",
    "**/.env.*",
    "**/application_default_credentials.json",
    "**/*.pem",
    "**/*.key",
    "**/*.pfx",
    "**/*.p12",
    "**/terraform.tfstate",
    "**/terraform.tfstate.backup",
    "**/*.enc.yaml",
    "**/*.enc.yml",
    "**/*.enc.json",
    "/tmp/sops*",
    "/tmp/op*",
    "/tmp/bw*",
    "/tmp/bws*",
    "/tmp/secret*",
    "/private/tmp/sops*",
    "/private/tmp/op*",
    "/private/tmp/bw*",
    "/private/tmp/bws*",
    "/private/tmp/secret*",
]

NOT_GLOBS = [
    "~/.kube/cache/**",
    "~/.kube/http-cache/**",
    "**/*.pub",
    "**/known_hosts",
    "**/*.example",
    "**/*.sample",
]

SOPS_CONTENT_MARKERS = ["sops:", "ENC[AES256_GCM"]
SOPS_SNIFF_EXTENSIONS = {".yaml", ".yml", ".json", ".env", ".ini"}
READ_COMMANDS = {
    "awk",
    "bat",
    "cat",
    "cut",
    "grep",
    "head",
    "jq",
    "less",
    "more",
    "nvim",
    "strings",
    "tail",
    "tr",
    "vim",
}

SAFE_KUBECTL_PIPE_RE = re.compile(r"\|\s*kubectl\s+(apply|diff)\b[^|;&]*\s-f\s+-(\s|$)")
KUSTOMIZE_RE = re.compile(r"\b(kustomize\s+build|kubectl\s+kustomize|kubectl\s+apply\b[^|;&]*\s-k\b)")


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print("block-secret-exposure: invalid hook input: %s" % error, file=sys.stderr)
        return 1

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    cwd = data.get("cwd") or os.getcwd()

    reason = ""
    if tool_name == "Bash":
        reason = check_bash(tool_input.get("command", ""), cwd)
    elif tool_name == "Read":
        reason = check_read(tool_input.get("file_path", ""), cwd)
    elif tool_name == "Grep":
        reason = check_grep(tool_input, cwd)

    if reason:
        deny(reason)
    return 0


def check_bash(command, cwd):
    command = command.strip()
    if not command:
        return ""

    lower = command.lower()

    if command_substitutes_secret(command):
        return "Command substitution around secret reads is blocked because it can print the value later."

    if "op_run_no_masking" in lower or re.search(r"\bop\b[^|;&]*\brun\b[^|;&]*--no-masking\b", lower):
        return "1Password output masking must stay enabled."

    if re.search(r"\bop\b[^|;&]*\bread\b", lower):
        return "Direct op read to Claude output is blocked. Use op run for trusted subprocesses."

    if re.search(r"\bbw\s+get\s+(password|item|notes|totp|attachment)\b", lower):
        return "Direct Bitwarden bw get output is blocked because it can expose secret values."

    if re.search(r"\bbws\s+secret\s+(get|list)\b", lower):
        return "Direct Bitwarden Secrets Manager output is blocked because secret values are present in JSON."

    if re.search(r"\bbws\s+run\b", lower) and prints_environment_or_secret(command):
        return "bws run with env/echo-style output is blocked; use it only for trusted consumers."

    if re.search(r"\bkubectl\s+get\s+secrets?\b", lower) and re.search(r"-o\s*(yaml|json|jsonpath)|--output[=\s]*(yaml|json|jsonpath)", lower):
        return "kubectl get secret with yaml/json/jsonpath output is blocked. List keys or describe the secret instead."

    if uses_sops_exec(command):
        if sops_exec_prints_secret(command):
            return "sops exec-env/exec-file with env/echo-style output is blocked."
        return ""

    if uses_sops_decrypt(command):
        if is_safe_kubectl_pipe(command):
            return ""
        if is_safe_sops_tempfile(command):
            return ""
        return "SOPS decrypt is blocked unless piped to kubectl apply/diff or redirected to a mktemp file with an immediate cleanup trap."

    if "ksops" in lower:
        if is_safe_kubectl_pipe(command):
            return ""
        return "KSOPS output is blocked unless piped directly to kubectl apply/diff."

    if KUSTOMIZE_RE.search(lower) and kustomize_uses_ksops(command, cwd):
        if is_safe_kubectl_pipe(command):
            return ""
        return "kustomize/ksops output is blocked because it can contain decrypted Kubernetes Secrets."

    sensitive_path = bash_sensitive_read_path(command, cwd)
    if sensitive_path:
        return "Reading sensitive file '%s' is blocked. Use stat, wc -l, or grep -c for existence/count checks only." % sensitive_path

    return ""


def check_read(raw_path, cwd):
    path = resolve_path(raw_path, cwd)
    if path and (is_sensitive_path(path) or has_sops_marker(path)):
        return "Read tool access to '%s' is blocked. Use grep -c for a key name, stat, or wc -l instead." % display_path(path)
    return ""


def check_grep(tool_input, cwd):
    for raw_path in grep_candidate_paths(tool_input):
        path = resolve_path(raw_path, cwd)
        if path and (is_sensitive_path(path) or has_sops_marker(path)):
            return "Grep tool access to '%s' is blocked. Use grep -c from Bash for a key name or stat/wc -l instead." % display_path(path)
    return ""


def command_substitutes_secret(command):
    secret_words = r"(op|bw|bws|sops)"
    secret_actions = r"(read|decrypt|get|secret|-d|--decrypt)"
    if re.search(r"\$\([^)]*\b%s\b[^)]*\b%s\b[^)]*\)" % (secret_words, secret_actions), command, re.IGNORECASE):
        return True
    if re.search(r"`[^`]*\b%s\b[^`]*\b%s\b[^`]*`" % (secret_words, secret_actions), command, re.IGNORECASE):
        return True
    return False


def prints_environment_or_secret(command):
    return bool(re.search(r"\b(env|printenv|set|export|declare|echo|printf|cat|less|more|head|tail|tee|pbcopy)\b", command, re.IGNORECASE))


def sops_exec_prints_secret(command):
    tokens = shell_tokens(command)
    for index, token in enumerate(tokens):
        if token in {"exec-env", "exec-file"}:
            consumer = " ".join(tokens[index + 2:])
            return prints_environment_or_secret(consumer)
    return prints_environment_or_secret(command)


def uses_sops_decrypt(command):
    lower = command.lower()
    return bool(re.search(r"\bsops\b[^|;&]*(\s-d\b|\s--decrypt\b|\sdecrypt\b)", lower))


def uses_sops_exec(command):
    lower = command.lower()
    return bool(re.search(r"\bsops\b[^|;&]*(\sexec-file\b|\sexec-env\b)", lower))


def is_safe_kubectl_pipe(command):
    return bool(SAFE_KUBECTL_PIPE_RE.search(command))


def is_safe_sops_tempfile(command):
    lower = command.lower()
    has_mktemp = "mktemp" in lower and "/tmp/sops" in lower
    has_trap = "trap" in lower and "rm -f" in lower and "exit int term" in lower
    redirects_to_tmpfile = bool(re.search(r">\s*['\"]?\$\{?TMPFILE\}?['\"]?", command))
    return has_mktemp and has_trap and redirects_to_tmpfile


def kustomize_uses_ksops(command, cwd):
    if "ksops" in command.lower():
        return True

    target = kustomize_target(command)
    target_path = resolve_path(target or ".", cwd)
    if not target_path:
        return False

    if target_path.is_file():
        candidates = [target_path]
    else:
        candidates = [
            target_path / "kustomization.yaml",
            target_path / "kustomization.yml",
            target_path / "Kustomization",
        ]

    for candidate in candidates:
        try:
            text = candidate.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if "generators:" in text and "ksops" in text:
            return True

    return False


def kustomize_target(command):
    tokens = shell_tokens(first_pipeline_part(command))
    if not tokens:
        return "."

    if tokens[:2] == ["kustomize", "build"]:
        return first_non_option(tokens[2:]) or "."

    if len(tokens) >= 2 and tokens[0:2] == ["kubectl", "kustomize"]:
        return first_non_option(tokens[2:]) or "."

    if len(tokens) >= 3 and tokens[0:2] == ["kubectl", "apply"]:
        for index, token in enumerate(tokens):
            if token == "-k" and index + 1 < len(tokens):
                return tokens[index + 1]
            if token.startswith("-k") and len(token) > 2:
                return token[2:]
    return "."


def first_non_option(tokens):
    skip_next = False
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        if token in {"-o", "--output", "--load-restrictor", "--enable-helm"}:
            skip_next = True
            continue
        if not token.startswith("-"):
            return token
    return ""


def bash_sensitive_read_path(command, cwd):
    for segment in shell_command_segments(command):
        tokens = shell_tokens(segment)
        if not tokens:
            continue

        tokens = strip_leading_assignments(tokens)
        if not tokens:
            continue

        tool = Path(tokens[0]).name
        if tool in READ_COMMANDS:
            sensitive_path = sensitive_read_command_path(tool, tokens, cwd)
            if sensitive_path:
                return sensitive_path

    for match in re.finditer(r"<\s*([^<>\s]+)", command):
        path = resolve_path(match.group(1), cwd)
        if path and (is_sensitive_path(path) or has_sops_marker(path)):
            return display_path(path)

    return ""


def shell_command_segments(command):
    segments = []
    current = []
    quote = ""
    escaped = False
    index = 0

    while index < len(command):
        char = command[index]

        if escaped:
            current.append(char)
            escaped = False
            index += 1
            continue

        if char == "\\":
            current.append(char)
            escaped = True
            index += 1
            continue

        if quote:
            current.append(char)
            if char == quote:
                quote = ""
            index += 1
            continue

        if char in {"'", '"'}:
            quote = char
            current.append(char)
            index += 1
            continue

        if command.startswith("&&", index) or command.startswith("||", index):
            append_segment(segments, current)
            current = []
            index += 2
            continue

        if char in {"|", ";", "\n"}:
            append_segment(segments, current)
            current = []
            index += 1
            continue

        current.append(char)
        index += 1

    append_segment(segments, current)
    return segments


def append_segment(segments, chars):
    segment = "".join(chars).strip()
    if segment:
        segments.append(segment)


def strip_leading_assignments(tokens):
    tokens = list(tokens)
    while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
        tokens.pop(0)
    return tokens


def sensitive_read_command_path(tool, tokens, cwd):
    if tool == "grep" and grep_is_count_only(tokens):
        return ""

    for token in read_command_path_args(tool, tokens):
        path = resolve_path(token, cwd)
        if path and (is_sensitive_path(path) or has_sops_marker(path)):
            return display_path(path)

    return ""


def read_command_path_args(tool, tokens):
    args = tokens[1:]
    if tool == "grep":
        return grep_path_args(args)
    if tool == "awk":
        return awk_path_args(args)
    if tool == "jq":
        return jq_path_args(args)
    return generic_path_args(args)


def generic_path_args(args):
    paths = []

    for index, arg in enumerate(args):
        if arg == "--":
            paths.extend(args[index + 1:])
            break
        if arg.startswith("-"):
            continue
        paths.append(arg)

    return paths


def grep_path_args(args):
    paths = []
    pattern_seen = False
    skip_next = False

    for index, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg == "--":
            remaining = list(args[index + 1:])
            if not pattern_seen and remaining:
                remaining = remaining[1:]
            paths.extend(remaining)
            break
        if arg in {"-e", "--regexp", "-f", "--file"}:
            skip_next = True
            pattern_seen = True
            continue
        if arg.startswith("--regexp=") or arg.startswith("--file="):
            pattern_seen = True
            continue
        if arg.startswith("-"):
            continue
        if not pattern_seen:
            pattern_seen = True
            continue
        paths.append(arg)

    return paths


def grep_is_count_only(tokens):
    for token in tokens[1:]:
        if token == "--":
            return False
        if token == "--count" or token.startswith("--count="):
            return True
        if token.startswith("--"):
            continue
        if token.startswith("-") and "c" in token:
            return True
    return False


def awk_path_args(args):
    paths = []
    program_seen = False
    skip_next = False

    for index, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg == "--":
            paths.extend(args[index + 1:])
            break
        if arg in {"-f", "-v"}:
            skip_next = True
            continue
        if arg.startswith("-"):
            continue
        if not program_seen:
            program_seen = True
            continue
        paths.append(arg)

    return paths


def jq_path_args(args):
    paths = []
    filter_seen = False
    skip_next = False

    for index, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg == "--":
            paths.extend(args[index + 1:])
            break
        if arg in {"-f", "--from-file", "-L", "--arg", "--argjson", "--slurpfile", "--rawfile", "--args", "--jsonargs"}:
            skip_next = True
            continue
        if arg.startswith("--from-file="):
            continue
        if arg.startswith("-"):
            continue
        if not filter_seen:
            filter_seen = True
            continue
        paths.append(arg)

    return paths


def grep_candidate_paths(tool_input):
    raw_path = tool_input.get("path", "")
    raw_glob = tool_input.get("glob", "")

    candidates = []
    for value in (raw_path, raw_glob):
        if isinstance(value, str) and value.strip():
            candidates.append(value)

    if isinstance(raw_path, str) and raw_path.strip() and isinstance(raw_glob, str) and raw_glob.strip():
        expanded_glob = os.path.expanduser(os.path.expandvars(raw_glob.strip()))
        if not Path(expanded_glob).is_absolute():
            candidates.append(str(Path(raw_path.strip()) / raw_glob.strip()))

    return candidates


def first_pipeline_part(command):
    return re.split(r"\||&&|\|\||;", command, 1)[0]


def shell_tokens(command):
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def resolve_path(raw_path, cwd):
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


def is_sensitive_path(path):
    return matches_any(path, SENSITIVE_FILE_GLOBS) and not matches_any(path, NOT_GLOBS)


def has_sops_marker(path):
    if not path or not path.exists() or not path.is_file():
        return False

    if path.suffix.lower() not in SOPS_SNIFF_EXTENSIONS and not path.name.startswith(".env"):
        return False

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")[:2048]
    except OSError:
        return False

    return any(marker in text for marker in SOPS_CONTENT_MARKERS)


def matches_any(path, patterns):
    path_text = str(path)
    path_name = path.name

    for pattern in patterns:
        expanded = os.path.expanduser(pattern)
        short_pattern = pattern[3:] if pattern.startswith("**/") else pattern
        expanded_base = expanded[:-3] if expanded.endswith("/**") else ""
        pattern_base = pattern[:-3] if pattern.endswith("/**") else ""

        if expanded_base and (path_text == expanded_base or path_text.startswith(expanded_base + "/")):
            return True
        if pattern_base and (path_text == pattern_base or path_text.startswith(pattern_base + "/")):
            return True
        if fnmatch.fnmatch(path_text, expanded):
            return True
        if fnmatch.fnmatch(path_text, pattern):
            return True
        if fnmatch.fnmatch(path_name, short_pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(path_text, "*/" + short_pattern):
            return True

    return False


def display_path(path):
    home = Path.home()
    try:
        return "~/" + str(path.relative_to(home))
    except ValueError:
        return str(path)


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "SECRET_GUARD: " + reason,
        }
    }))


if __name__ == "__main__":
    raise SystemExit(main())
