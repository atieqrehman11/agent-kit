#!/usr/bin/env bash
#
# ── Modes ───────────────────────────────────────────────────────────────────
#   ./run_local.sh [env]          build the artifact and validate the bundle
#   ./run_local.sh deploy [env]   build, validate, then deploy to DEV
#
#   env: dev (default) | stg | prod | all
#
# `deploy` targets dev whatever env you build. stg and prod go through the CI/CD
# controller on merge, and it deploys the artifact you COMMITTED — so build `all`
# before promoting, or stg deploys a stale space.
#
# The views and functions the space reads are NOT deployed by the bundle: DAB has
# no resource for arbitrary SQL. Apply src/{views,functions}/*.sql to the catalog
# yourself before the space can answer anything.
set -euo pipefail

cd "$(dirname "$0")"

MODE="run"
case "${1:-}" in
  deploy)     MODE=deploy; shift ;;
  run)        shift ;;
  -h|--help)  sed -n '/^# ── Modes/,/^$/p' "$0"; exit 0 ;;
esac

ENV="${1:-dev}"
case "$ENV" in
  dev|stg|prod|all) ;;
  *) echo "usage: $0 [run|deploy] [dev|stg|prod|all]" >&2; exit 2 ;;
esac

command -v databricks >/dev/null || { echo "ERROR: databricks CLI not found" >&2; exit 2; }

# genie_spaces needs CLI 1.3.0+; below that this bundle will not even parse.
ver=$(databricks --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
if [ "$(printf '%s\n1.3.0\n' "$ver" | sort -V | head -1)" != "1.3.0" ]; then
  echo "ERROR: Databricks CLI $ver is too old — genie_spaces needs 1.3.0+." >&2
  exit 2
fi

# Artifacts are committed: the controller clones fresh and runs no project scripts.
echo "── Building ($ENV) ──"
PYTHONPATH=python python3 python/validate.py
if [ "$ENV" = all ]; then
  for e in dev stg prod; do PYTHONPATH=python python3 python/build_space.py --env "$e"; done
else
  PYTHONPATH=python python3 python/build_space.py --env "$ENV"
fi

echo "── Validating the bundle ──"
databricks bundle validate -t dev

if [ "$MODE" != "deploy" ]; then
  exit 0
fi

echo "── Deploying to dev ──"
databricks bundle deploy -t dev

echo
databricks bundle summary -t dev | sed -n '/Resources:/,$p'
echo
echo "Commit generated/space.*.json — the controller deploys what is in git,"
echo "not what your laptop just built."
