#!/usr/bin/env bash
# Runs one lab test suite headless against nvim-next and appends its results
# into ~/tmp/nvim-next-lab/results-<phase>.md.
#
# Usage: nvim-lab/run.sh <java|python|go|misc|smoke> <baseline|after>
set -euo pipefail

SUITE="${1:?usage: run.sh <java|python|go|misc|smoke> <baseline|after>}"
PHASE="${2:?usage: run.sh <java|python|go|misc|smoke> <baseline|after>}"

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT="${LAB_ROOT:-$HOME/tmp/nvim-next-lab}"
RESULTS_FILE="$LAB_ROOT/results-$PHASE.md"
NVIM_BIN="$HOME/.local/opt/neovim/next/bin/nvim"

case "$SUITE" in
	smoke) SCRIPT="$LAB_DIR/lua/smoke_test.lua" ;;
	java) SCRIPT="$LAB_DIR/lua/java_test.lua" ;;
	python) SCRIPT="$LAB_DIR/lua/python_test.lua" ;;
	go) SCRIPT="$LAB_DIR/lua/go_test.lua" ;;
	misc) SCRIPT="$LAB_DIR/lua/misc_test.lua" ;;
	*)
		echo "Unknown suite: $SUITE" >&2
		exit 1
		;;
esac

mkdir -p "$LAB_ROOT"
RAW_LOG="$(mktemp /tmp/nvim-lab-XXXXXX.log)"
trap 'rm -f "$RAW_LOG"' EXIT

NVIM_APPNAME=nvim-next LAB_ROOT="$LAB_ROOT" LAB_PHASE="$PHASE" \
	"$NVIM_BIN" --headless -c "lua dofile('$SCRIPT')" >"$RAW_LOG" 2>&1 || true

RESULT_LINES="$(grep '^RESULT' "$RAW_LOG" || true)"

if [ "$SUITE" = "smoke" ]; then
	if [ -z "$RESULT_LINES" ] || echo "$RESULT_LINES" | grep -q $'\tFAIL\t'; then
		echo "$RESULT_LINES"
		cat "$RAW_LOG" >&2
		exit 1
	fi
	echo "$RESULT_LINES"
	exit 0
fi

{
	echo ""
	echo "## $SUITE ($PHASE) — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
	echo ""
	if [ -z "$RESULT_LINES" ]; then
		echo "NO RESULT LINES CAPTURED — raw log follows:"
		echo '```'
		cat "$RAW_LOG"
		echo '```'
	else
		echo "$RESULT_LINES" | while IFS=$'\t' read -r _ row status note; do
			echo "- [$status] $row — $note"
		done
	fi
} >>"$RESULTS_FILE"

echo "$RESULT_LINES"
