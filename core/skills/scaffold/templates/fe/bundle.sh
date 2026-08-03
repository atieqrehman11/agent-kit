#!/bin/bash
set -euo pipefail

# ==============================================================================
# LOCAL DEV-LOOP deploy — builds this front end and deploys it to the DEV
# workspace as a Databricks App.
#
# dist/ is a build artifact and is not committed, so the build must happen
# before every deploy. That is the whole reason this repo deploys itself rather
# than triggering the shared DAB controller: the controller deploys from a git
# checkout, which has no dist/ in it.
#
# stg / prod are CLOUD deploys owned by .gitlab-ci.yml (merge to the `stg` or
# `prod` branch). This script refuses any target other than dev on purpose.
#
# Usage: chmod +x bundle.sh && ./bundle.sh
# ==============================================================================

APP_NAME="TPLVAR_SLUG"
APP_RESOURCE_KEY="TPLVAR_RESOURCE_KEY"
BUNDLE_TARGET="${BUNDLE_TARGET:-dev}"

if [ "$BUNDLE_TARGET" != "dev" ]; then
  echo "ERROR: bundle.sh only deploys to dev. stg/prod deploy from .gitlab-ci.yml" >&2
  echo "       (merge to the stg/prod branch)." >&2
  exit 1
fi

SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SOURCE_DIR"

DATABRICKS_BIN="${DATABRICKS_BIN:-databricks}"

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm is required but was not found in PATH (see .nvmrc for the version)." >&2
  exit 1
fi

if ! command -v "$DATABRICKS_BIN" >/dev/null 2>&1; then
  echo "ERROR: Databricks CLI is required but was not found in PATH." >&2
  echo "       Install: brew tap databricks/tap && brew install databricks" >&2
  exit 1
fi

if ! "$DATABRICKS_BIN" bundle --help >/dev/null 2>&1 || ! "$DATABRICKS_BIN" apps --help >/dev/null 2>&1; then
  echo "ERROR: Databricks CLI version does not support 'bundle' and 'apps' commands." >&2
  exit 1
fi

echo "==> Bundle Deploy — $APP_NAME"
echo "    Target: $BUNDLE_TARGET"

# Step 1: Install exactly what package-lock.json pins
echo "==> Step 1: Installing dependencies (npm ci)..."
if [ -f package-lock.json ]; then
  npm ci
else
  echo "    No package-lock.json yet — running npm install (commit the lockfile after)."
  npm install
fi

# Step 2: Verify before deploying anything
# Same gate CI runs. A deploy that skips it puts a build nobody checked in front
# of users, and the feedback then arrives from a person rather than a pipeline.
echo "==> Step 2: Verifying (format, lint, types, tests, build, bundle budget)..."
npm run verify

# Step 3: Confirm the artifact the app will actually serve exists
echo "==> Step 3: Checking build output..."
if [ ! -f dist/index.html ]; then
  echo "ERROR: dist/index.html was not produced by the build." >&2
  exit 1
fi
echo "    dist/ has $(find dist -type f | wc -l | tr -d ' ') files"

# Step 4: Clear local sync state, so a deleted asset does not linger in the workspace
echo "==> Step 4: Clearing local sync state..."
rm -rf "$SOURCE_DIR/.databricks/bundle"

# Step 5: Validate
echo "==> Step 5: Validating bundle..."
"$DATABRICKS_BIN" bundle validate -t "$BUNDLE_TARGET"

# Step 6: Deploy
echo "==> Step 6: Deploying bundle..."
"$DATABRICKS_BIN" bundle deploy -t "$BUNDLE_TARGET"

# Step 7: Run app resource
echo "==> Step 7: Running app resource..."
"$DATABRICKS_BIN" bundle run "$APP_RESOURCE_KEY" -t "$BUNDLE_TARGET"

# Step 8: Verify
echo "==> Step 8: Verifying..."
"$DATABRICKS_BIN" apps get "$APP_NAME"
echo "==> Done!"
