#!/bin/bash
# Adapted from spotify/portal-ai-plugins/plugins/shunt/evals/run.sh (Apache-2.0)
# Haiku variant: tests local haiku shunt hooks + haiku.sh transport, no Portal needed
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# Local paths
HOOK_READ="$PLUGIN_DIR/hooks/check-file-size"
HOOK_BASH="$PLUGIN_DIR/hooks/check-bash-read"
HAIKU_LIB="$PLUGIN_DIR/scripts/shunt/lib/haiku.sh"
FIXTURES="$SCRIPT_DIR/.fixtures"
PASSED=0; FAILED=0; TOTAL=0

generate_fixture() { local p="$1" l="$2"; if [ "$l" -eq 0 ]; then touch "$p"; else seq 1 "$l" | awk '{print "line "NR}' > "$p"; fi; }
setup_fixtures() {
  local evals_file="$1"; rm -rf "$FIXTURES"; mkdir -p "$FIXTURES"
  local count; count=$(jq '.evals | length' "$evals_file")
  for ((i=0;i<count;i++)); do
    local fixture; fixture=$(jq -r ".evals[$i].fixture" "$evals_file"); [ "$fixture" = "null" ] && continue
    local lines; lines=$(jq -r ".evals[$i].fixture.lines" "$evals_file")
    local input_path; input_path=$(jq -r ".evals[$i].input.tool_input.file_path // empty" "$evals_file")
    if [ -z "$input_path" ]; then input_path=$(jq -r ".evals[$i].input.tool_input.command // empty" "$evals_file" | sed -E 's/^(cat|head|tail|less|more) +(-[^ ]+ +)*//' | sed 's/ .*//' | tr -d '"'"'")
    fi
    input_path=$(echo "$input_path" | sed "s|{{FIXTURES}}|$FIXTURES|")
    case "$input_path" in "$FIXTURES"/*) generate_fixture "$input_path" "$lines";; esac
  done
}
run_eval() {
  local hook="$1" name="$2" input="$3" expected="$4" reason="$5" env_json="$6"; TOTAL=$((TOTAL+1))
  local result actual
  if [ -n "$env_json" ] && [ "$env_json" != "null" ]; then
    local env_cmd=""; while IFS='=' read -r key val; do env_cmd="$env_cmd $key=$val"; done < <(echo "$env_json" | jq -r 'to_entries[] | "\(.key)=\(.value)"')
    result=$(echo "$input" | env $env_cmd bash "$hook" 2>/dev/null)
  else result=$(echo "$input" | bash "$hook" 2>/dev/null); fi
  actual=$(echo "$result" | jq -r '.decision')
  if [ "$actual" = "$expected" ]; then printf "  \033[32mPASS\033[0m  %-30s %s\n" "$name" "$reason"; PASSED=$((PASSED+1)); else printf "  \033[31mFAIL\033[0m  %-30s expected=%s got=%s\n" "$name" "$expected" "$actual"; FAILED=$((FAILED+1)); fi
}
run_suite() {
  local hook="$1" evals_file="$2" label="$3"; setup_fixtures "$evals_file"
  echo ""; echo "$label"; echo "────────────────────────────────────────────────────────────────"
  local count; count=$(jq '.evals | length' "$evals_file")
  for ((i=0;i<count;i++)); do
    local name expected reason input env_json
    name=$(jq -r ".evals[$i].name" "$evals_file"); expected=$(jq -r ".evals[$i].expected_decision" "$evals_file"); reason=$(jq -r ".evals[$i].reason" "$evals_file")
    input=$(jq -c ".evals[$i].input" "$evals_file" | sed "s|{{FIXTURES}}|$FIXTURES|g"); env_json=$(jq -r ".evals[$i].env // empty" "$evals_file")
    run_eval "$hook" "$name" "$input" "$expected" "$reason" "$env_json"
  done; rm -rf "$FIXTURES"
}

run_transport_haiku() {
  echo ""; echo "Transport (scripts/shunt/lib/haiku.sh, deterministic fallback)"; echo "────────────────────────────────────────────────────────────────"
  set +e
  # shellcheck source=../scripts/shunt/lib/haiku.sh
  . "$HAIKU_LIB"
  local workdir msg rc out
  workdir=$(mktemp -d); msg="$workdir/msg.txt"
  printf 'line one\nline two\n' > "$msg"
  # Stub claude to fail auth so fallback triggers
  claude() { echo "Not logged in" >&2; echo ""; return 1; }
  export -f claude
  # Test bulk-reader fallback produces outline and respects payload limit
  local mf="$workdir/bulk-msg.txt"
  {
    printf '<file path="/tmp/fake.py">\n'; cat "$msg"; printf '</file>\n'; printf 'Question: test?\n'
  } > "$mf"
  out=$(shunt_invoke bulk-reader "$mf" 2>&1); rc=$?
  if echo "$out" | grep -q "Question: test?"; then printf "  \033[32mPASS\033[0m  %-32s fallback returns question\n" "fallback-bulk"; PASSED=$((PASSED+1)); TOTAL=$((TOTAL+1)); else printf "  \033[31mFAIL\033[0m  %-32s fallback missing\n" "fallback-bulk"; FAILED=$((FAILED+1)); TOTAL=$((TOTAL+1)); fi
  # Payload limit
  SHUNT_MAX_PAYLOAD_BYTES=10 out=$(shunt_invoke bulk-reader "$mf" 2>&1) && rc=0 || rc=$?
  if [ $rc -ne 0 ] && echo "$out" | grep -q "over the 10 byte"; then printf "  \033[32mPASS\033[0m  %-32s payload limit enforced\n" "payload-ceiling"; PASSED=$((PASSED+1)); TOTAL=$((TOTAL+1)); else printf "  \033[31mFAIL\033[0m  %-32s payload limit\n" "payload-ceiling"; FAILED=$((FAILED+1)); TOTAL=$((TOTAL+1)); fi
  # code-writer requires reference -> we test preflight already allows bulk-reader
  unset -f claude; rm -rf "$workdir"; set -e
}

# Main
run_suite "$HOOK_READ" "$SCRIPT_DIR/hook-evals.json" "Read hook (check-file-size) — local haiku copy"
run_suite "$HOOK_BASH" "$SCRIPT_DIR/bash-hook-evals.json" "Bash hook (check-bash-read) — local haiku copy"
run_transport_haiku
echo ""; echo "════════════════════════════════════════════════════════════════"; printf "Total: \033[32m%d passed\033[0m, \033[31m%d failed\033[0m, %d total\n" "$PASSED" "$FAILED" "$TOTAL"; echo ""
[ "$FAILED" -gt 0 ] && exit 1; exit 0
