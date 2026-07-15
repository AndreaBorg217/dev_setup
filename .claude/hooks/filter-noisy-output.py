#!/usr/bin/env python3
"""
PreToolUse hook: rewrite noisy Bash commands so Claude receives focused output.

The file keeps its .sh name because settings invoke this path directly; the
shebang selects Python.
"""

import json
import re
import sys


# Bash hooks run blocker -> rtk -> this filter, so match commands after rtk rewrites them.
COMMAND_PREFIX = r"(?:rtk\s+)?"

TEST_CMDS = re.compile(
    r"^" + COMMAND_PREFIX + r"((npm|yarn|pnpm|bun)( run)? (test|test:[^ ]+|jest|vitest)|"
    r"pytest|python -m pytest|go test|cargo test|mvn test|gradle test|"
    r"\./gradlew test|rspec|bundle exec rspec|mix test|dotnet test|"
    r"phpunit|vendor/bin/phpunit|jest|vitest)(\s|$)"
)

LINT_CMDS = re.compile(
    r"^" + COMMAND_PREFIX + r"((npm|yarn|pnpm|bun)( run)? "
    r"(lint|lint:[^ ]+|typecheck|type-check|check|check:[^ ]+)|"
    r"eslint|tsc|ruff|mypy|golangci-lint|flake8|pylint|black --check|"
    r"prettier --check|shellcheck|yamllint|hadolint|cargo clippy)(\s|$)"
)

BUILD_CMDS = re.compile(
    r"^" + COMMAND_PREFIX + r"((npm|yarn|pnpm|bun)( run)? (build|build:[^ ]+)|go build|"
    r"cargo build|mvn (package|compile|install)|gradle build|"
    r"\./gradlew build|make|cmake --build|dotnet build|tsc -b|"
    r"next build|vite build|webpack|rollup|docker build|docker buildx build|"
    r"docker compose build|docker-compose build)(\s|$)"
)

INSTALL_CMDS = re.compile(
    r"^" + COMMAND_PREFIX + r"((npm|yarn|pnpm|bun) (install|i|add)|pip install|"
    r"python -m pip install|poetry (install|add)|uv (sync|add|pip install)|"
    r"go get|go mod download|cargo (add|update)|bundle (install|add)|"
    r"composer (install|require)|mvn dependency:resolve|docker pull|"
    r"docker compose pull|docker-compose pull|helm dependency (build|update))(\s|$)"
)

LOG_CMDS = re.compile(
    r"^" + COMMAND_PREFIX + r"((docker|kubectl|argo|pm2|heroku|vercel|fly|railway) logs|"
    r"argocd app logs|docker compose logs|docker-compose logs|stern|"
    r"kubetail|journalctl|tail)(\s|$)"
)

OPS_CMDS = re.compile(
    r"^" + COMMAND_PREFIX + r"(kubectl (describe|get events|events)|kubectl argo rollouts "
    r"(get|status)|argo (get|watch|wait)|argocd app "
    r"(get|resources|sync|wait)|helm "
    r"(lint|test|status|install|upgrade))(\s|$)"
)

TEST_GREP = (
    r"FAIL|FAILED|ERROR|Error|error:|panic:|AssertionError|Traceback|"
    r"Exception|Caused by|Expected|Received|--- FAIL|FAILURES"
)
BUILD_GREP = (
    r"FAIL|FAILED|ERROR|Error|error:|fatal:|panic:|Traceback|Exception|"
    r"undefined reference|cannot find|not found|No such file|Module not found|"
    r"Compilation failed|BUILD FAILED|unauthorized|denied|no matching manifest"
)
LOG_GREP = (
    r"FAIL|FAILED|ERROR|Error|error:|fatal:|panic:|Traceback|Exception|"
    r"WARN|Warning|warning|timeout|refused|denied|not found|unhandled|"
    r"stack|BackOff|CrashLoopBackOff|ImagePullBackOff|ErrImagePull|OOMKilled|"
    r"Evicted|Unhealthy|Readiness probe failed|Liveness probe failed"
)
OPS_GREP = (
    r"FAIL|FAILED|ERROR|Error|error:|fatal:|panic:|Traceback|Exception|"
    r"WARN|Warning|warning|Failed|BackOff|CrashLoopBackOff|"
    r"ImagePullBackOff|ErrImagePull|OOMKilled|Evicted|FailedScheduling|"
    r"Unhealthy|Degraded|OutOfSync|Missing|Progressing|Suspended|Unknown|"
    r"DeadlineExceeded|Forbidden|Unauthorized|denied|connection refused|no such host"
)
INSTALL_NOISE = (
    r"^(npm WARN|npm notice|Fetching|Downloading|Downloaded|Progress|"
    r"Resolving|Resolved|Installing|Installed|Pulling fs layer|Waiting|Download complete|"
    r"Verifying Checksum|Pull complete|Digest:|Status:)"
)


def response(command):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {"command": command},
        }
    }


def filtered_command(command):
    if TEST_CMDS.search(command):
        return f"{command} 2>&1 | grep -A 8 -B 2 -E '{TEST_GREP}' | head -150"

    if LINT_CMDS.search(command):
        return f"{command} 2>&1 | head -150"

    if BUILD_CMDS.search(command):
        return f"{command} 2>&1 | grep -A 8 -B 2 -E '{BUILD_GREP}' | head -150"

    if INSTALL_CMDS.search(command):
        return f"{command} 2>&1 | grep -v -E '{INSTALL_NOISE}' | head -200"

    if LOG_CMDS.search(command):
        return f"{command} 2>&1 | grep -A 8 -B 2 -E '{LOG_GREP}' | head -200"

    if OPS_CMDS.search(command):
        return f"{command} 2>&1 | grep -A 10 -B 3 -E '{OPS_GREP}' | head -200"

    return None


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        print("{}")
        return

    if not isinstance(input_data, dict):
        print("{}")
        return

    tool_input = input_data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        print("{}")
        return

    command = tool_input.get("command", "")
    if not isinstance(command, str):
        print("{}")
        return

    rewritten = filtered_command(command)
    if rewritten is None:
        print("{}")
        return

    print(json.dumps(response(rewritten), separators=(",", ":")))


if __name__ == "__main__":
    main()
