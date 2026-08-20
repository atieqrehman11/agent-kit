#!/usr/bin/env bash
#
# Run TPLVAR_SLUG locally, or deploy it to the DEV workspace.
#
# ── Modes ───────────────────────────────────────────────────────────────────
#   ./run_local.sh            Vite dev server on :5173 — HMR, no build
#   ./run_local.sh prod       build, then server.mjs on :8000 — what deploys
#   ./run_local.sh deploy     deploy to the DEV workspace
#
# `deploy` targets dev only. stg and prod belong to the CI/CD controller, which
# deploys the committed dist/ from a fresh clone.
#
# Configuration, from your shell or .env.local:
#   BACKEND_API_UPSTREAM   the API to proxy /api/* to           (required)
#   BACKEND_API_TOKEN      workspace token, when that API is a deployed App
#   PORT                   override the port
#   SKIP_VERIFY=1          deploy without running `pnpm run verify` first
#
# A busy port is cleared first: SIGTERM, then SIGKILL if it does not let go.
set -euo pipefail

cd "$(dirname "$0")"

# Must match the resource key in resources/fe.app.yml.
APP_KEY="TPLVAR_RESOURCE_KEY"

# pnpm, because pnpm-lock.yaml is the lockfile and Databricks Apps picks the
# manager from it. npx runs it when it is not installed globally.
if command -v pnpm >/dev/null; then PM=(pnpm); else PM=(npx --yes pnpm@10); fi

MODE="${1:-dev}"
case "$MODE" in
  dev)    PORT="${PORT:-5173}" ;;
  prod)   PORT="${PORT:-8000}" ;;
  deploy) ;;
  -h|--help) sed -n '/^# ── Modes/,/^$/p' "$0"; exit 0 ;;
  *) echo "usage: $0 [dev|prod|deploy]" >&2; exit 2 ;;
esac

# ── Deploy to the dev workspace ─────────────────────────────────────────────
# CI runs no Node job, so this is the only place a broken build is caught before
# it reaches a workspace. dist/ is committed — rebuild and commit it whenever
# src/ changes, or stg deploys green and serves a stale bundle.
if [[ "$MODE" == "deploy" ]]; then
  command -v databricks >/dev/null || { echo "ERROR: databricks CLI not found" >&2; exit 2; }

  echo "── Validating bundle ──"
  databricks bundle validate -t dev

  if [[ "${SKIP_VERIFY:-}" == "1" ]]; then
    echo "── Skipping verify (SKIP_VERIFY=1) ──"
  else
    echo "── Verify ──"
    [[ -d node_modules ]] || "${PM[@]}" install
    "${PM[@]}" run verify
  fi

  echo "── Deploying to dev ──"
  databricks bundle deploy -t dev

  # deploy uploads and registers; `run` creates the app deployment that makes
  # the upload live. Skipping it leaves the previous version serving.
  echo "── Creating app deployment ──"
  databricks bundle run "$APP_KEY" -t dev

  echo
  databricks bundle summary -t dev | sed -n '/Resources:/,$p'
  exit 0
fi

# ── Free the port ───────────────────────────────────────────────────────────
# Only TCP listeners are targeted, so a browser holding a client connection on
# the same port is left alone.
free_port() {
  local port="$1" pids
  pids=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)
  [[ -z "$pids" ]] && return 0

  echo "Port $port is in use:"
  ps -o pid=,comm=,args= -p $pids 2>/dev/null | cut -c1-100 | sed 's/^/  /'

  kill $pids 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.3
    pids=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)
    [[ -z "$pids" ]] && { echo "  → released"; return 0; }
  done

  echo "  → still held, sending SIGKILL"
  kill -9 $pids 2>/dev/null || true
  sleep 0.5
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "ERROR: could not free port $port" >&2; exit 1
  fi
  echo "  → released"
}

# Vite loads .env.local itself, but the checks below run before Vite does — so
# source it here too, or a setup whose upstream lives only in .env.local is
# wrongly refused.
if [[ -f .env.local ]]; then
  set -a; . ./.env.local; set +a
fi

if [[ -z "${BACKEND_API_UPSTREAM:-}" ]]; then
  echo "ERROR: BACKEND_API_UPSTREAM is not set." >&2
  echo "       In prod mode server.mjs has no backend; in dev mode the proxy" >&2
  echo "       route is never registered and /api calls 404." >&2
  exit 2
fi

# A deployed Databricks App sits behind OAuth and answers 401 without a token.
if [[ "$BACKEND_API_UPSTREAM" == *databricksapps.com* && -z "${BACKEND_API_TOKEN:-}" ]]; then
  echo "WARNING: upstream is a deployed App but BACKEND_API_TOKEN is unset —" >&2
  echo "         proxied calls will 401." >&2
fi

[[ -d node_modules ]] || { echo "Installing dependencies…"; "${PM[@]}" install; }

free_port "$PORT"

echo
echo "mode     : $MODE"
echo "port     : $PORT"
echo "upstream : $BACKEND_API_UPSTREAM"
echo

if [[ "$MODE" == "dev" ]]; then
  exec npx vite --port "$PORT" --strictPort
else
  "${PM[@]}" run build
  PORT="$PORT" exec node server.mjs
fi
