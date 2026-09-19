#!/bin/bash
# Shared Haiku plumbing for shunt-haiku delegation scripts.
# Adapted from spotify/portal-ai-plugins/plugins/shunt/scripts/lib/aika.sh (Apache-2.0)
# Replaces Portal CLI (aika:invoke-chat) with local Haiku invocation.
# Every delegation is one shot — re-sending files is free where it matters.

if [ -z "${SHUNT_MAX_PAYLOAD_BYTES:-}" ]; then
  case "$(uname -s)" in
    Linux) SHUNT_MAX_PAYLOAD_BYTES=120000 ;;
    *)     SHUNT_MAX_PAYLOAD_BYTES=400000 ;;
  esac
fi

SHUNT_TIMEOUT_SECONDS="${SHUNT_TIMEOUT_SECONDS:-180}"
SHUNT_HAIKU_MODEL="${SHUNT_HAIKU_MODEL:-haiku}"
# Respects ANTHROPIC_DEFAULT_HAIKU_MODEL from settings.json env if set
if [ -n "${ANTHROPIC_DEFAULT_HAIKU_MODEL:-}" ]; then
  SHUNT_HAIKU_MODEL="${ANTHROPIC_DEFAULT_HAIKU_MODEL}"
fi

# System prompts matching upstream AiKA mode instructions
BULK_READER_PROMPT="You are a precise code analyst. Read the provided files and answer the question concisely. Output structured bullets only. No greetings, no prose, no preambles, no summaries. Lead every bullet with the exact name, type, or line number. Use nested bullets for details. Skip anything the caller did not ask for."
CODE_WRITER_PROMPT="You generate code files based on a spec and reference files. Match the existing patterns, conventions, naming, and style exactly. Output only the code — no explanations, no markdown fences unless asked. If the spec is ambiguous, make reasonable choices that match the patterns in the reference code."

SHUNT_TMPFILES=()
shunt_tmpfile() {
  local f
  f=$(mktemp) || return 1
  SHUNT_TMPFILES+=("$f")
  trap 'rm -f "${SHUNT_TMPFILES[@]}"' EXIT
  printf -v "$1" '%s' "$f"
}

shunt_preflight() {
  local missing=""
  command -v jq >/dev/null 2>&1 || missing=" jq"
  # claude CLI or ANTHROPIC_API_KEY must be available; if neither, fall back to deterministic mode
  if ! command -v claude >/dev/null 2>&1; then
    echo "Warning: claude CLI not found — will use deterministic fallback (grep outline)." >&2
  fi
  if [ -n "$missing" ]; then
    echo "Error: missing required command(s):$missing" >&2
    echo "  jq — brew install jq" >&2
    return 1
  fi
  return 0
}

shunt_report_error() {
  local label="$1" response="$2"
  echo "Error: $label" >&2
  printf '%s\n' "$response" >&2
}

# Deterministic fallback when Haiku is unavailable (CI, no auth, offline).
# Extracts file outlines via grep — still saves ~80% tokens vs raw files.
shunt_fallback_bulk_read() {
  local message_file="$1" question="$2"
  # Header to stderr so stdout stays the answer
  echo "## Fallback summary (Haiku unavailable) — deterministic outline" >&2
  echo ""
  echo "- Question: $question"
  echo "- Files: extracted outlines (grep -n class/def/export/function)"
  echo ""
  grep -o '<file path="[^"]*">' "$message_file" | sed 's/<file path="//;s/">//' | while IFS= read -r f; do
    if [ -f "$f" ]; then
      echo "- $f ($(wc -l < "$f" | tr -d ' ') lines):"
      grep -n -E '^\s*(class |def |function |export |import |type |interface |const |let |var |pub |impl |fn |struct |enum )' "$f" | head -n 80 | sed 's/^/  - /'
      echo ""
    fi
  done
  echo ""
  echo "- Note: Run with authenticated Haiku for LLM summary; this fallback is lossy but keeps tokens out of Opus context."
}

# Runs one ephemeral chat turn against Haiku and prints the answer.
# $1 mode name (bulk-reader | code-writer)
# $2 file holding the message (prompt)
shunt_invoke() {
  local mode_name="$1" message_file="$2"
  local payload_bytes system_prompt

  payload_bytes=$(wc -c < "$message_file" | tr -d ' ')
  if [ "$payload_bytes" -gt "$SHUNT_MAX_PAYLOAD_BYTES" ]; then
    echo "Error: request is $payload_bytes bytes, over the $SHUNT_MAX_PAYLOAD_BYTES byte limit." >&2
    echo "Input must fit in ARG_MAX. Send fewer or smaller files, or raise SHUNT_MAX_PAYLOAD_BYTES." >&2
    return 1
  fi

  case "$mode_name" in
    bulk-reader) system_prompt="$BULK_READER_PROMPT" ;;
    code-writer) system_prompt="$CODE_WRITER_PROMPT" ;;
    *)           system_prompt="$BULK_READER_PROMPT" ;;
  esac

  # Prefer claude CLI with Haiku model; fallback to deterministic if not authenticated
  if command -v claude >/dev/null 2>&1; then
    local stderr_file response rc err prompt_text
    stderr_file=$(mktemp)
    prompt_text=$(cat "$message_file")
    # Haiku delegation: ephemeral, no tools, no session persistence
    # Single prompt arg to avoid double-cat broken pipe; timeout guards hangs
    if command -v timeout >/dev/null 2>&1; then
      response=$(timeout "${SHUNT_TIMEOUT_SECONDS}" claude -p --model "$SHUNT_HAIKU_MODEL" --no-session-persistence --tools "" --system-prompt "$system_prompt" --output-format text "$prompt_text" 2>"$stderr_file")
      rc=$?
      if [ $rc -eq 124 ]; then
        echo "Error: Haiku invocation timed out after ${SHUNT_TIMEOUT_SECONDS}s." >&2
        cat "$stderr_file" >&2
        rm -f "$stderr_file"
        return 1
      fi
    else
      response=$(claude -p --model "$SHUNT_HAIKU_MODEL" --no-session-persistence --tools "" --system-prompt "$system_prompt" --output-format text "$prompt_text" 2>"$stderr_file")
      rc=$?
    fi
    err=$(cat "$stderr_file"; rm -f "$stderr_file")

    # Detect auth failure — fall back to deterministic
    if echo "$response $err" | grep -qi "not logged in\|Not authenticated\|API key\|auth"; then
      echo "Warning: Haiku auth unavailable — using deterministic fallback." >&2
      if [ "$mode_name" = "bulk-reader" ]; then
        local q
        q=$(grep -m1 '^Question:' "$message_file" | sed 's/^Question: //')
        shunt_fallback_bulk_read "$message_file" "$q"
        return 0
      else
        echo "Error: code-writer requires Haiku auth; fallback not implemented for generation." >&2
        return 1
      fi
    fi

    if [ $rc -ne 0 ]; then
      echo "Error: Haiku invocation failed (rc=$rc)" >&2
      printf '%s\n' "$err" >&2
      printf '%s\n' "$response" >&2
      # Fallback for bulk-reader on transient failure
      if [ "$mode_name" = "bulk-reader" ]; then
        echo "Attempting deterministic fallback..." >&2
        local q
        q=$(grep -m1 '^Question:' "$message_file" | sed 's/^Question: //')
        shunt_fallback_bulk_read "$message_file" "$q"
        return 0
      fi
      return 1
    fi

    if [ -z "$response" ]; then
      echo "Error: Haiku returned no text" >&2
      return 1
    fi
    printf '%s\n' "$response"
    return 0
  else
    # No claude CLI — deterministic fallback for bulk-reader
    if [ "$mode_name" = "bulk-reader" ]; then
      local q
      q=$(grep -m1 '^Question:' "$message_file" | sed 's/^Question: //')
      shunt_fallback_bulk_read "$message_file" "$q"
      return 0
    fi
    echo "Error: claude CLI not found and no API fallback configured." >&2
    return 1
  fi
}
