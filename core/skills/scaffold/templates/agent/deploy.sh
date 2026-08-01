#!/usr/bin/env bash
# Create/update the multi-agent supervisor from supervisor/ config (scripted, no UI).
set -euo pipefail
cd "$(dirname "$0")"

# ── Databricks auth ──────────────────────────────────────────────────────────
# Default SDK auth chain: DATABRICKS_HOST + DATABRICKS_TOKEN, or a CLI profile
# (DATABRICKS_CONFIG_PROFILE). If no PAT is set and the CLI token is missing or
# expired, log in first (opens a browser).
PROFILE="${DATABRICKS_CONFIG_PROFILE:-}"
if [[ -z "${DATABRICKS_TOKEN:-}" ]]; then
  if command -v databricks >/dev/null 2>&1; then
    if ! databricks auth token ${PROFILE:+--profile "$PROFILE"} >/dev/null 2>&1; then
      echo "==> Databricks auth missing/expired — launching login${PROFILE:+ (profile $PROFILE)}..."
      databricks auth login ${PROFILE:+--profile "$PROFILE"}
    fi
  else
    echo "WARN: databricks CLI not found and DATABRICKS_TOKEN unset — auth may fail." >&2
  fi
fi

python3 -m pip install -q -r requirements.txt
python3 src/deploy.py --config supervisor/supervisor.yml "$@"
