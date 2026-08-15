#!/bin/bash
set -euo pipefail

# ── Modes ───────────────────────────────────────────────────────────────────
#   ./run_local.sh            validate the space declaration (no credentials needed)
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


cd "$(dirname "$0")"   # paths below are repo-relative, so run from anywhere
# Local Genie deploy — applies backing-view DDL, then create/update the space.
# Needs DATABRICKS_HOST + DATABRICKS_TOKEN (or a configured CLI profile) and a
# warehouse_id set in genie-space/space.yml.
#
# Local deploys target dev. Pass --env stg / --env prod only if you are pointed at
# that workspace on purpose; normally stg and prod are deployed by CI on a branch
# merge (.gitlab-ci.yml), against credentials this laptop does not hold.
python3 -m pip install -q -r requirements.txt
python3 src/deploy.py --apply-ddl "$@"
