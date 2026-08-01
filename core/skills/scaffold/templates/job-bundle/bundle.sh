#!/bin/bash
set -e

# ==============================================================================
# LOCAL DEV-LOOP deploy — deploys this job bundle to the DEV workspace only.
#
# stg / prod are CLOUD deploys owned by the CI/CD controller: merge to the `stg`
# or `prod` branch and .gitlab-ci.yml triggers the controller. This script
# refuses any target other than dev on purpose — do not deploy to prod locally.
#
# Usage: ./bundle.sh
# ==============================================================================

BUNDLE_TARGET="${BUNDLE_TARGET:-dev}"
JOB_KEY="TPLVAR_RESOURCE_KEY_job"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
DATABRICKS_BIN="${DATABRICKS_BIN:-databricks}"

if [ "$BUNDLE_TARGET" != "dev" ]; then
  echo "ERROR: bundle.sh only deploys to dev. stg/prod go through the CI/CD" >&2
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
