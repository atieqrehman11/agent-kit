#!/usr/bin/env bash
#
# GitLab PROJECT setup — run per repo, or across a whole group.
#
#   1. create dev / stg / prod branches from the default branch
#   2. branch protection — main/stg/prod are MR-only, dev takes direct pushes
#   3. set the default branch
#   4. add the DAB controller to the CI/CD job-token inbound allowlist
#
# The group-level pieces (trigger token, service account) are setup-group.sh —
# they are inherited, so doing them per project is N writes for one grant.
#
# DRY RUN BY DEFAULT — nothing is written until you pass --apply.
#
#   ./setup-repo.sh --project 12345678
#   ./setup-repo.sh --group 12345678 --apply        # every project in the group
#
set -euo pipefail
. "$(dirname "$0")/_common.sh"

# From the profile sheet — the controller is per platform, not per repo.
CONTROLLER_PROJECT_ID="${CONTROLLER_PROJECT_ID:-}"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-dev}"   # where work lands; main is the release record

# Repos that are not deployable bundles: no env branches, no controller access.
SKIP_PROJECTS="${SKIP_PROJECTS:-platform-registry}"

# 0 = no direct push, MR only. 30 = developer, 40 = maintainer.
#
# dev takes direct pushes: it is the integration branch, and the gate that
# matters is dev → stg, which triggers a real deploy.
#
# Raising a push level does NOT unprotect the branch. Protected-branch status is
# what exposes protected CI variables such as CONTROLLER_TRIGGER_TOKEN — remove
# it and the trigger silently gets an empty token.
PUSH_LEVEL="${PUSH_LEVEL:-0}"
PUSH_LEVEL_DEV="${PUSH_LEVEL_DEV:-30}"
PUSH_LEVEL_STG="${PUSH_LEVEL_STG:-0}"   # set 30 to push straight to stg and deploy
MERGE_LEVEL_DEV="${MERGE_LEVEL_DEV:-30}"
MERGE_LEVEL_STG="${MERGE_LEVEL_STG:-30}"
MERGE_LEVEL_PROD="${MERGE_LEVEL_PROD:-40}"
MERGE_LEVEL_MAIN="${MERGE_LEVEL_MAIN:-40}"

APPLY=0
GROUP_ID=""
PROJECT_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --group)      GROUP_ID="$2"; shift 2 ;;
    --project)    PROJECT_ID="$2"; shift 2 ;;
    --controller) CONTROLLER_PROJECT_ID="$2"; shift 2 ;;
    --apply)      APPLY=1; shift ;;
    -h|--help)    sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$GROUP_ID$PROJECT_ID" ]] || { echo "ERROR: pass --group or --project" >&2; exit 2; }

start_up

list_projects() {
  if [[ -n "$PROJECT_ID" ]]; then echo "$PROJECT_ID"; return; fi
  local page=1 ids
  while :; do
    api GET "/groups/$GROUP_ID/projects?per_page=100&page=$page&include_subgroups=true&archived=false"
    if [[ "$API_STATUS" != "200" ]]; then
      echo "ERROR: listing group $GROUP_ID failed — HTTP $API_STATUS: $API_BODY" >&2
      exit 1
    fi
    ids=$(printf '%s' "$API_BODY" | jq -r '.[].id')
    [[ -z "$ids" ]] && break
    echo "$ids"
    page=$((page + 1))
  done
}

configure_project() {
  local pid="$1"

  api GET "/projects/$pid"
  if [[ "$API_STATUS" != "200" ]]; then
    echo "  ✗ cannot read project $pid — HTTP $API_STATUS" >&2
    FAILURES=$((FAILURES + 1)); return
  fi
  local path default
  path=$(printf '%s' "$API_BODY" | jq -r '.path_with_namespace')
  default=$(printf '%s' "$API_BODY" | jq -r '.default_branch // empty')

  echo "  $path (id $pid)"
  local INDENT="    "

  local name="${path##*/}" skip
  for skip in $SKIP_PROJECTS; do
    [[ "$name" == "$skip" ]] && { say "– not a deployable bundle — skipping"; return; }
  done

  # archived=false in the listing does not exclude these.
  if [[ "$(printf '%s' "$API_BODY" | jq -r '.marked_for_deletion_on // empty')" != "" ]]; then
    say "– scheduled for deletion — skipping"; return
  fi
  if [[ "$(printf '%s' "$API_BODY" | jq -r '.empty_repo')" == "true" ]]; then
    say "! no commits yet — push an initial commit, then re-run" >&2
    FAILURES=$((FAILURES + 1)); return
  fi
  if [[ -z "$default" ]]; then
    say "! no default branch visible — you likely lack repository access here" >&2
    FAILURES=$((FAILURES + 1)); return
  fi

  # 1. Branches
  local branch
  for branch in dev stg prod; do
    api GET "/projects/$pid/repository/branches/$branch"
    if [[ "$API_STATUS" == "200" ]]; then
      say "✓ branch $branch exists"; continue
    fi
    if (( APPLY )); then
      api POST "/projects/$pid/repository/branches" \
        "$(jq -nc --arg b "$branch" --arg r "$default" '{branch:$b, ref:$r}')"
      ok "branch $branch created from $default" 201 || true
    else would "create branch $branch from $default"; fi
  done

  # 2. Protection — rewritten only when it differs, so a re-run never briefly
  #    unprotects a branch that was already correct.
  #
  #    Literal names, not $DEFAULT_BRANCH: with dev as the default, matching on
  #    it would give dev main's rules and process it twice while skipping main.
  local merge_level push_level cur_push cur_merge
  for branch in main dev stg prod; do
    push_level="$PUSH_LEVEL"
    case "$branch" in
      main) merge_level="$MERGE_LEVEL_MAIN" ;;
      prod) merge_level="$MERGE_LEVEL_PROD" ;;
      stg)  merge_level="$MERGE_LEVEL_STG"; push_level="$PUSH_LEVEL_STG" ;;
      dev)  merge_level="$MERGE_LEVEL_DEV"; push_level="$PUSH_LEVEL_DEV" ;;
    esac

    api GET "/projects/$pid/protected_branches/$branch"
    if [[ "$API_STATUS" == "200" ]]; then
      cur_push=$(printf '%s' "$API_BODY" | jq -r '.push_access_levels[0].access_level // -1')
      cur_merge=$(printf '%s' "$API_BODY" | jq -r '.merge_access_levels[0].access_level // -1')
      if [[ "$cur_push" == "$push_level" && "$cur_merge" == "$merge_level" ]]; then
        say "✓ $branch protected (push $push_level / merge $merge_level)"; continue
      fi
      if (( APPLY )); then
        api DELETE "/projects/$pid/protected_branches/$branch"
        ok "$branch protection cleared for update" 204 200 || true
      else
        would "re-protect $branch (currently push $cur_push / merge $cur_merge)"; continue
      fi
    elif (( ! APPLY )); then
      would "protect $branch (push $push_level / merge $merge_level)"; continue
    fi

    api POST "/projects/$pid/protected_branches" \
      "$(jq -nc --arg n "$branch" --argjson p "$push_level" --argjson m "$merge_level" \
         '{name:$n, push_access_level:$p, merge_access_level:$m, allow_force_push:false}')"
    ok "$branch protected (push $push_level / merge $merge_level)" 201 || true
  done

  # 3. Default branch
  if [[ "$default" == "$DEFAULT_BRANCH" ]]; then
    say "✓ default branch is $DEFAULT_BRANCH"
  else
    api GET "/projects/$pid/repository/branches/$DEFAULT_BRANCH"
    if [[ "$API_STATUS" != "200" ]]; then
      say "! $DEFAULT_BRANCH does not exist; leaving default as $default" >&2
    elif (( APPLY )); then
      api PUT "/projects/$pid" "$(jq -nc --arg b "$DEFAULT_BRANCH" '{default_branch:$b}')"
      ok "default branch set to $DEFAULT_BRANCH" 200 || true
    else would "set default branch $default → $DEFAULT_BRANCH"; fi
  fi

  # 4. Job-token allowlist — per-project only; there is no group equivalent.
  if [[ -z "$CONTROLLER_PROJECT_ID" ]]; then
    say "– no controller id (CONTROLLER_PROJECT_ID / --controller); skipping allowlist"
    return
  fi
  api GET "/projects/$pid/job_token_scope/allowlist"
  if [[ "$API_STATUS" == "200" ]] &&
     printf '%s' "$API_BODY" | jq -e --argjson c "$CONTROLLER_PROJECT_ID" 'any(.id == $c)' >/dev/null; then
    say "✓ controller in job-token allowlist"
  elif (( APPLY )); then
    api POST "/projects/$pid/job_token_scope/allowlist" \
      "$(jq -nc --argjson c "$CONTROLLER_PROJECT_ID" '{target_project_id:$c}')"
    ok "controller added to job-token allowlist" 201 || true
  else would "add controller ($CONTROLLER_PROJECT_ID) to job-token allowlist"; fi
}

PROJECTS=$(list_projects)
COUNT=$(printf '%s\n' "$PROJECTS" | grep -c . || true)
echo
echo "Configuring $COUNT project(s)."
echo

for pid in $PROJECTS; do
  configure_project "$pid"
  echo
done

finish
