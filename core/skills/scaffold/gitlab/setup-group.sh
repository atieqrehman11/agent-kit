#!/usr/bin/env bash
#
# GitLab GROUP setup — run once per team group, not per repo.
#
#   - CONTROLLER_TRIGGER_TOKEN variable (protected + masked)
#   - the Databricks service account as a member
#
# Both are inherited by every project in the group, including ones created
# later, which is why they belong here rather than in setup-repo.sh.
#
# DRY RUN BY DEFAULT — nothing is written until you pass --apply.
#
#   ./setup-group.sh --group 12345678
#   CONTROLLER_TRIGGER_TOKEN=glptt-… ./setup-group.sh --group 12345678 --apply
#
# The token value is only needed the first time; afterwards the group already
# has it and this reports it as present. Never paste it into a file or a chat —
# export it in your own shell.
#
set -euo pipefail
. "$(dirname "$0")/_common.sh"

# Defaults come from the profile sheet, not from this file — they differ per
# client. Override with the flags or the environment.
SVC_ACCOUNT="${SVC_ACCOUNT:-TODO_SET_DATABRICKS_SERVICE_ACCOUNT}"
SVC_ACCESS_LEVEL="${SVC_ACCESS_LEVEL:-20}"   # 20 = Reporter (read-only)

APPLY=0
GROUP_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --group)   GROUP_ID="$2"; shift 2 ;;
    --account) SVC_ACCOUNT="$2"; shift 2 ;;
    --apply)   APPLY=1; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$GROUP_ID" ]] || { echo "ERROR: pass --group <id>" >&2; exit 2; }

start_up
echo
echo "Group $GROUP_ID"

# ── Controller trigger token ────────────────────────────────────────────────
api GET "/groups/$GROUP_ID/variables/CONTROLLER_TRIGGER_TOKEN"
if [[ "$API_STATUS" == "200" ]]; then
  say "✓ CONTROLLER_TRIGGER_TOKEN already set"
elif [[ -z "${CONTROLLER_TRIGGER_TOKEN:-}" ]]; then
  say "! CONTROLLER_TRIGGER_TOKEN missing — export it and re-run, or pipelines cannot trigger the controller" >&2
  FAILURES=$((FAILURES + 1))
elif (( ! APPLY )); then
  would "create CONTROLLER_TRIGGER_TOKEN (protected + masked)"
else
  api POST "/groups/$GROUP_ID/variables" \
    "$(jq -nc --arg v "$CONTROLLER_TRIGGER_TOKEN" \
       '{key:"CONTROLLER_TRIGGER_TOKEN", value:$v, protected:true, masked:true, variable_type:"env_var"}')"
  ok "CONTROLLER_TRIGGER_TOKEN created (protected + masked)" 201 || true
fi

# ── Databricks service account ──────────────────────────────────────────────
if [[ "$SVC_ACCOUNT" == TODO_SET_* ]]; then
  say "– no service account configured (SVC_ACCOUNT / --account); skipping"
else
  api GET "/users?username=$SVC_ACCOUNT"
  SVC_USER_ID=""
  [[ "$API_STATUS" == "200" ]] && SVC_USER_ID=$(printf '%s' "$API_BODY" | jq -r '.[0].id // empty')

  if [[ -z "$SVC_USER_ID" ]]; then
    say "! service account '$SVC_ACCOUNT' not found — skipping" >&2
    FAILURES=$((FAILURES + 1))
  else
    api GET "/groups/$GROUP_ID/members/$SVC_USER_ID"
    if [[ "$API_STATUS" == "200" ]]; then
      say "✓ $SVC_ACCOUNT is already a member"
    elif (( ! APPLY )); then
      would "add $SVC_ACCOUNT (access $SVC_ACCESS_LEVEL)"
    else
      api POST "/groups/$GROUP_ID/members" \
        "$(jq -nc --argjson u "$SVC_USER_ID" --argjson a "$SVC_ACCESS_LEVEL" \
           '{user_id:$u, access_level:$a}')"
      ok "$SVC_ACCOUNT added (access $SVC_ACCESS_LEVEL)" 201 || true
    fi
  fi
fi

echo
finish
