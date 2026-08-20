#!/usr/bin/env bash
#
# ── Modes ───────────────────────────────────────────────────────────────────
#   ./run_local.sh            validate src/managed/ — no credentials, no network
#   ./run_local.sh plan       reconcile against DEV in dry-run: report, apply nothing
#   ./run_local.sh deploy     deploy the bundle to DEV, then run the deploy job
#
# `deploy` targets dev only. stg and prod belong to the CI/CD controller, which
# does the same two steps — `bundle deploy` then `bundle run deploy_agent`.
#
# `plan` is the one check validate cannot do: whether a deploy would DELETE a
# tool from the live agent. Any tool not declared in src/managed/agent.yml is
# removed, including anything added through the Agents-tab UI.
set -euo pipefail

cd "$(dirname "$0")"

# Must match the resource key in resources/deploy.job.yml.
JOB_KEY="deploy_agent"

MODE="${1:-run}"
case "$MODE" in
  run|plan|deploy) ;;
  -h|--help) sed -n '/^# ── Modes/,/^$/p' "$0"; exit 0 ;;
  *) echo "usage: $0 [run|plan|deploy]" >&2; exit 2 ;;
esac

echo "── Validating src/managed/ ──"
PYTHONPATH=python python3 python/validate.py

if [[ "$MODE" == "run" ]]; then
  exit 0
fi

command -v databricks >/dev/null || { echo "ERROR: databricks CLI not found" >&2; exit 2; }

# `plan` runs the reconciler locally against dev with --dry-run. It authenticates
# with your ~/.databrickscfg profile rather than the bundle's run_as, so it shows
# what YOU would change — close enough to review a tool deletion before it happens.
if [[ "$MODE" == "plan" ]]; then
  echo "── Planning against dev (dry run) ──"
  PYTHONPATH=python python3 python/deploy_agent.py \
    --spec-dir src --dry-run \
    --var "display_name=$(databricks bundle summary -t dev -o json \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["variables"]["agent_display_name"]["value"])')"
  exit 0
fi

echo "── Validating the bundle ──"
databricks bundle validate -t dev

echo "── Deploying to dev ──"
databricks bundle deploy -t dev

# deploy only UPLOADS the spec and registers the job. The reconciler has to run
# for the agent to change at all — this is the step the controller also performs,
# driven by run_resources.yml.
echo "── Running the deploy job ──"
databricks bundle run "$JOB_KEY" -t dev

echo
databricks bundle summary -t dev | sed -n '/Resources:/,$p'
