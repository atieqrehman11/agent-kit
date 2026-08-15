#!/bin/bash
set -euo pipefail

# ── Modes ───────────────────────────────────────────────────────────────────
#   ./run_local.sh            serve the API on :8000 with reload
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
  ./.venv/bin/pip install -q -r requirements.txt
  exec ./.venv/bin/uvicorn app:app --reload --port "${PORT:-8000}"
  exit $?
fi



# ==============================================================================
# LOCAL DEV-LOOP deploy — deploys this app bundle to the DEV workspace only.
#
# stg / prod are CLOUD deploys owned by the CI/CD controller: merge to the `stg`
# or `prod` branch and .gitlab-ci.yml triggers the controller. This script
# refuses any target other than dev on purpose — do not deploy to prod locally.
#
# Usage: chmod +x bundle.sh && ./bundle.sh
# ==============================================================================

# App name (databricks apps get) and bundle resource key (databricks bundle run).
# Both must match databricks.yml — resources.apps.<key> and its name: field.
APP_NAME="TPLVAR_SLUG"
APP_RESOURCE_KEY="TPLVAR_RESOURCE_KEY"
BUNDLE_TARGET="${BUNDLE_TARGET:-dev}"

if [ "$BUNDLE_TARGET" != "dev" ]; then
  echo "ERROR: bundle.sh only deploys to dev. stg/prod go through the CI/CD" >&2
  echo "       controller (merge to the stg/prod branch)." >&2
  exit 1
fi
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_VERSION="3.11"
PYTHON_ABI="cp${PYTHON_VERSION/./}"
PLATFORM="manylinux2014_x86_64"
WHEELS_DIR="$SOURCE_DIR/wheels"
# Must match databricks.yml root_path (keyed on ${bundle.name}, not the app name).
BUNDLE_NAME="TPLVAR_BUNDLE_NAME"
WORKSPACE_ROOT="/Workspace/Shared/TPLVAR_PROJECT/TPLVAR_SLUG/.bundle/$BUNDLE_NAME/$BUNDLE_TARGET"
WORKSPACE_WHEELS_DIR="$WORKSPACE_ROOT/files/wheels"

PYTHON_BIN="${PYTHON_BIN:-python3}"
DATABRICKS_BIN="${DATABRICKS_BIN:-databricks}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN is required but was not found in PATH." >&2
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

if "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  PIP_CMD=("$PYTHON_BIN" -m pip)
elif command -v pip3 >/dev/null 2>&1; then
  PIP_CMD=(pip3)
else
  echo "ERROR: pip is required." >&2
  exit 1
fi

echo "==> Bundle Deploy — $APP_NAME"
echo "    Target: $BUNDLE_TARGET"
echo "    Pip:    ${PIP_CMD[*]}"

# Step 1: Download dependency wheels
echo "==> Step 1: Downloading dependency wheels..."
mkdir -p "$WHEELS_DIR"

REQUIREMENTS="$SOURCE_DIR/requirements.txt"
if [ -f "$REQUIREMENTS.bak" ]; then
  cp "$REQUIREMENTS.bak" "$REQUIREMENTS"
  echo "    Restored original requirements.txt from backup"
elif grep -q "^--no-index" "$REQUIREMENTS"; then
  sed -i.bak '/^--no-index/d;/^--find-links/d' "$REQUIREMENTS"
  rm -f "$REQUIREMENTS.bak"
  echo "    Stripped offline flags from requirements.txt"
fi

for pre_installed in databricks-sql-connector databricks-sdk; do
  if grep -q "^${pre_installed}" "$REQUIREMENTS"; then
    sed -i.bak "/^${pre_installed}/d" "$REQUIREMENTS"
    rm -f "$REQUIREMENTS.bak"
    echo "    Removed ${pre_installed} (pre-installed in Databricks runtime)"
  fi
done

find "$WHEELS_DIR" -type f -name "*.whl" -delete
find "$WHEELS_DIR" -type f -name "*.tar.gz" -delete

echo "    Downloading Linux wheels ($PLATFORM / $PYTHON_ABI)..."
"${PIP_CMD[@]}" download -r "$REQUIREMENTS" \
  -d "$WHEELS_DIR" \
  --python-version "$PYTHON_VERSION" \
  --implementation cp \
  --abi "$PYTHON_ABI" \
  --platform "$PLATFORM" \
  --only-binary=:all:

echo "    Downloaded $(find "$WHEELS_DIR" -maxdepth 1 -type f | wc -l) wheels"

# Step 2: Patch requirements.txt for offline install
echo "==> Step 2: Patching requirements.txt for offline install..."
if ! grep -q "^--no-index" "$REQUIREMENTS"; then
  cp "$REQUIREMENTS" "$REQUIREMENTS.bak"
  { echo "--no-index"; echo "--find-links wheels/"; echo ""; cat "$REQUIREMENTS.bak"; } > "$REQUIREMENTS"
fi

# Step 3: Clear stale remote wheels and local sync state
echo "==> Step 3: Clearing stale remote cache and local sync state..."
cd "$SOURCE_DIR"
"$DATABRICKS_BIN" workspace delete "$WORKSPACE_WHEELS_DIR" --recursive >/dev/null 2>&1 || true
rm -rf "$SOURCE_DIR/.databricks/bundle"

# Step 4: Validate
echo "==> Step 4: Validating bundle..."
"$DATABRICKS_BIN" bundle validate -t "$BUNDLE_TARGET"

# Step 5: Deploy
echo "==> Step 5: Deploying bundle..."
"$DATABRICKS_BIN" bundle deploy -t "$BUNDLE_TARGET"

# Step 6: Run app resource
echo "==> Step 6: Running app resource..."
"$DATABRICKS_BIN" bundle run "$APP_RESOURCE_KEY" -t "$BUNDLE_TARGET"

# Step 7: Verify
echo "==> Step 7: Verifying..."
"$DATABRICKS_BIN" apps get "$APP_NAME"
echo "==> Done!"
