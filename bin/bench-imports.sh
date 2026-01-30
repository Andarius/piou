#!/usr/bin/env bash
# Benchmark import times for piou
#
# Usage:
#   ./bin/bench-imports.sh              # Print results
#   ./bin/bench-imports.sh --json       # Output JSON for CI
#
# Requires: hyperfine, jq, uv

set -euo pipefail

# Ensure consistent decimal separator
export LC_NUMERIC=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WARMUP="${WARMUP:-3}"
RUNS="${RUNS:-10}"
JSON_OUTPUT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --json) JSON_OUTPUT=true; shift ;;
        --warmup) WARMUP="$2"; shift 2 ;;
        --runs) RUNS="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Create temp files and venv
CORE_JSON=$(mktemp)
RICH_JSON=$(mktemp)
TUI_JSON=$(mktemp)
TEMP_VENV=$(mktemp -d)
trap "rm -f $CORE_JSON $RICH_JSON $TUI_JSON; rm -rf $TEMP_VENV" EXIT

# Create temp venv without rich for baseline
uv venv "$TEMP_VENV" -q
uv pip install --python "$TEMP_VENV/bin/python" "$SCRIPT_DIR" -q
uv pip uninstall --python "$TEMP_VENV/bin/python" rich -q 2>/dev/null || true

# Run benchmarks
hyperfine --warmup "$WARMUP" --min-runs "$RUNS" \
    "$TEMP_VENV/bin/python -c \"from piou import Cli, Option\"" \
    --export-json "$CORE_JSON" >/dev/null 2>&1

hyperfine --warmup "$WARMUP" --min-runs "$RUNS" \
    'uv run python -c "from piou import Cli, Option"' \
    --export-json "$RICH_JSON" >/dev/null 2>&1

hyperfine --warmup "$WARMUP" --min-runs "$RUNS" \
    'uv run python -c "from piou.tui import TuiContext"' \
    --export-json "$TUI_JSON" >/dev/null 2>&1

# Extract results (rounded to 2 decimal places for cleaner output)
CORE_MEAN=$(jq '.results[0].mean * 1000 | . * 100 | round / 100' "$CORE_JSON")
CORE_STD=$(jq '.results[0].stddev * 1000 | . * 100 | round / 100' "$CORE_JSON")
RICH_MEAN=$(jq '.results[0].mean * 1000 | . * 100 | round / 100' "$RICH_JSON")
RICH_STD=$(jq '.results[0].stddev * 1000 | . * 100 | round / 100' "$RICH_JSON")
TUI_MEAN=$(jq '.results[0].mean * 1000 | . * 100 | round / 100' "$TUI_JSON")
TUI_STD=$(jq '.results[0].stddev * 1000 | . * 100 | round / 100' "$TUI_JSON")

if $JSON_OUTPUT; then
    cat <<EOF
[
  {"name": "piou (core)", "unit": "ms", "value": $CORE_MEAN, "range": $CORE_STD},
  {"name": "piou (rich)", "unit": "ms", "value": $RICH_MEAN, "range": $RICH_STD},
  {"name": "piou.tui", "unit": "ms", "value": $TUI_MEAN, "range": $TUI_STD}
]
EOF
else
    printf "\n📊 Import Benchmark Results:\n"
    printf "============================================================\n"
    printf "  %-30s %9.3fms (±%.3fms)\n" "piou (core)" "$CORE_MEAN" "$CORE_STD"
    printf "  %-30s %9.3fms (±%.3fms)\n" "piou (rich)" "$RICH_MEAN" "$RICH_STD"
    printf "  %-30s %9.3fms (±%.3fms)\n" "piou.tui" "$TUI_MEAN" "$TUI_STD"
    printf "============================================================\n"
    printf "  rich overhead:    +%.3fms\n" "$(jq -n "$RICH_MEAN - $CORE_MEAN")"
    printf "  textual overhead: +%.3fms\n" "$(jq -n "$TUI_MEAN - $RICH_MEAN")"
    printf "============================================================\n"
fi