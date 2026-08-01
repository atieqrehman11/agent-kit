#!/usr/bin/env bash
# agent-kit installer — dispatches to a tool adapter.
#
# Usage:
#   ./install.sh                        # install into ~/.claude (default target: claude)
#   ./install.sh --target claude        # same, explicit
#   ./install.sh --target claude ~/.claude
#   ./install.sh --list                 # show available adapters
#   ./install.sh --dry-run              # validate and report, write nothing
#
# core/ is tool-agnostic; everything tool-shaped lives in adapters/<tool>/. Adding a tool
# means adding an adapter — see STANDARD.md Part 2 for the contract it must satisfy, and
# adapters/claude/ for the reference implementation.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

usage() { awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; }

adapters() {
  for d in "$ROOT"/adapters/*/; do
    n="$(basename "$d")"
    if [[ -f "$d/install.py" || -f "$d/install.sh" ]]; then echo "$n"
    else echo "$n  (no installer — parked)"; fi
  done
}

TARGET_TOOL="claude"
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)   shift; TARGET_TOOL="${1:-}" ;;
    --target=*) TARGET_TOOL="${1#*=}" ;;
    --list)     adapters; exit 0 ;;
    -h|--help)  usage; exit 0 ;;
    *)          ARGS+=("$1") ;;
  esac
  shift
done

DIR="$ROOT/adapters/$TARGET_TOOL"
if [[ ! -d "$DIR" ]]; then
  printf 'unknown adapter: %s\n\navailable:\n' "$TARGET_TOOL" >&2
  adapters | sed 's/^/  /' >&2
  exit 2
fi
if [[ ! -f "$DIR/install.py" && ! -f "$DIR/install.sh" ]]; then
  printf 'adapter "%s" has no installer yet — it is parked.\nSee %s/README.md\n' \
    "$TARGET_TOOL" "$DIR" >&2
  exit 2
fi

if [[ -f "$DIR/install.py" ]]; then
  exec python3 "$DIR/install.py" ${ARGS+"${ARGS[@]}"}
else
  exec bash "$DIR/install.sh" ${ARGS+"${ARGS[@]}"}
fi
