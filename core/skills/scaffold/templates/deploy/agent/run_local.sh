#!/usr/bin/env bash
# Create/update the multi-agent supervisor from supervisor/ config (scripted, no UI).
#
# Local deploys target dev. Pass --env stg / --env prod only if you are pointed at
# that workspace on purpose; normally stg and prod are deployed by CI on a branch
# merge (.gitlab-ci.yml), against credentials this laptop does not hold.
set -euo pipefail

# ── Modes ───────────────────────────────────────────────────────────────────
#   ./run_local.sh            validate the supervisor declaration (no credentials needed)
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
  exec python3 src/validate.py "$@"
  exit $?
fi


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
python3 src/deploy.py "$@"
