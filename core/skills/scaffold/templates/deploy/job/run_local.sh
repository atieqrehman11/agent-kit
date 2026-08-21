#!/bin/bash
set -euo pipefail

# ── Modes ───────────────────────────────────────────────────────────────────
#   ./run_local.sh            run the job entrypoint locally
#   ./run_local.sh deploy     deploy to the DEV workspace
#
# deploy targets dev only. stg and prod go through the CI/CD controller, on
# merge to the stg / prod branch.
MODE="${1:-run}"
case "$MODE" in
  deploy) shift || true ;;
  run)    shift || true ;;
  -h|--help) sed -n '/^# ── Modes/,/^$/p' "$0"; exit 0 ;;
  *) echo "usage: $0 [run|deploy]" >&2; exit 2 ;;
esac

if [[ "$MODE" != "deploy" ]]; then
  cd "$(dirname "$0")"
  [[ -d .venv ]] || python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt 2>/dev/null || true
  exec ./.venv/bin/python src/main.py "$@"
  exit $?
fi



# ==============================================================================
# LOCAL DEV-LOOP deploy — deploys this job bundle to the DEV workspace only.
#
# stg / prod are CLOUD deploys owned by the CI/CD controller: merge to the `stg`
# or `prod` branch and .gitlab-ci.yml triggers the controller. This script
# refuses any target other than dev on purpose — do not deploy to prod locally.
#
# Usage: ./run_local.sh deploy
# ==============================================================================

BUNDLE_TARGET="${BUNDLE_TARGET:-dev}"
JOB_KEY="TPLVAR_RESOURCE_KEY"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
DATABRICKS_BIN="${DATABRICKS_BIN:-databricks}"

if [ "$BUNDLE_TARGET" != "dev" ]; then
  echo "ERROR: run_local.sh only deploys to dev. stg/prod go through the CI/CD" >&2
  echo "       controller (merge to the stg/prod branch)." >&2
  exit 1
fi

if ! command -v "$DATABRICKS_BIN" >/dev/null 2>&1; then
  echo "ERROR: Databricks CLI not found. Install: brew tap databricks/tap && brew install databricks" >&2
  exit 1
fi

echo "======================================================"
echo "  Job Bundle Deploy (DEV) — TPLVAR_SLUG"
echo "======================================================"

cd "$SOURCE_DIR"

echo "==> Validating..."
"$DATABRICKS_BIN" bundle validate -t dev

echo "==> Deploying to dev..."
"$DATABRICKS_BIN" bundle deploy -t dev

echo ""
echo "==> Done. To run the job in dev:"
echo "    databricks bundle run $JOB_KEY -t dev"
echo ""
