# Shared by setup-group.sh and setup-repo.sh. Sourced, never run.
#
# GitLab auth, first hit wins:
#   $GITLAB_TOKEN → glab → macOS keychain → git credential helper
# The header is probed at startup: glab stores OAuth tokens (Bearer), classic
# PATs use PRIVATE-TOKEN. The wrong one is a flat 401, so probing beats guessing.

API="${GITLAB_API:-https://gitlab.com/api/v4}"
API_HOST=$(printf '%s' "$API" | sed -E 's|^https?://||; s|/.*$||')
KEYCHAIN_ITEM="${KEYCHAIN_ITEM:-gitlab-token}"

FAILURES=0
INDENT="  "

# Braces are required: bash reads a following multi-byte glyph as part of the
# variable name, and set -u then aborts on "INDENT·: unbound variable".
say()   { echo "${INDENT}$*"; }
would() { echo "${INDENT}· would $*"; }

# Sets TOKEN and TOKEN_SOURCE. Not a $(...) call — a subshell loses TOKEN_SOURCE.
resolve_token() {
  if [[ -n "${GITLAB_TOKEN:-}" ]]; then TOKEN_SOURCE="\$GITLAB_TOKEN"; TOKEN="$GITLAB_TOKEN"; return; fi

  local t
  if command -v glab >/dev/null; then
    if t=$(glab config get token --host "$API_HOST" 2>/dev/null) && [[ -n "$t" ]]; then
      TOKEN_SOURCE="glab ($API_HOST)"; TOKEN="$t"; return
    fi
  fi

  if command -v security >/dev/null; then
    if t=$(security find-generic-password -s "$KEYCHAIN_ITEM" -w 2>/dev/null) && [[ -n "$t" ]]; then
      TOKEN_SOURCE="keychain item '$KEYCHAIN_ITEM'"; TOKEN="$t"; return
    fi
  fi

  if command -v git >/dev/null; then
    t=$(printf 'protocol=https\nhost=%s\n\n' "$API_HOST" \
        | git credential fill 2>/dev/null | sed -n 's/^password=//p' || true)
    if [[ -n "$t" ]]; then
      TOKEN_SOURCE="git credential helper ($API_HOST)"; TOKEN="$t"; return
    fi
  fi

  echo "ERROR: no GitLab token found. Set \$GITLAB_TOKEN, or run: glab auth login" >&2
  exit 2
}

AUTH_HEADER=""
API_STATUS=""
API_BODY=""
api() {
  local method="$1" path="$2" data="${3:-}"
  local args=(-sS -X "$method" -H "$AUTH_HEADER" -w $'\n%{http_code}')
  [[ -n "$data" ]] && args+=(-H 'Content-Type: application/json' -d "$data")
  local out
  if ! out=$(curl "${args[@]}" "$API$path"); then
    API_STATUS="000"; API_BODY="curl failed"; return 0
  fi
  API_STATUS=$(printf '%s' "$out" | tail -n1)
  API_BODY=$(printf '%s\n' "$out" | sed '$d')
}

probe_auth() {
  local h
  for h in "Authorization: Bearer $TOKEN" "PRIVATE-TOKEN: $TOKEN"; do
    AUTH_HEADER="$h"
    api GET "/user"
    if [[ "$API_STATUS" == "200" ]]; then
      echo "Authenticated as $(printf '%s' "$API_BODY" | jq -r '.username') via ${h%%:*}"
      return 0
    fi
  done
  echo "ERROR: token rejected (HTTP $API_STATUS). Try: glab auth login" >&2
  exit 1
}

ok() {
  local label="$1"; shift
  local s
  for s in "$@"; do
    # shellcheck disable=SC2053
    if [[ "$API_STATUS" == $s ]]; then echo "${INDENT}✓ $label ($API_STATUS)"; return 0; fi
  done
  echo "${INDENT}✗ $label — HTTP $API_STATUS: $(printf '%s' "$API_BODY" | head -c 200)" >&2
  FAILURES=$((FAILURES + 1))
  return 1
}

start_up() {
  command -v jq >/dev/null || { echo "ERROR: jq is required" >&2; exit 2; }
  (( APPLY )) || echo "── DRY RUN — nothing will be written. Re-run with --apply. ──"
  TOKEN=""; TOKEN_SOURCE=""
  resolve_token
  echo "GitLab token from: $TOKEN_SOURCE"
  probe_auth
}

finish() {
  if (( FAILURES )); then
    echo "Finished with $FAILURES failure(s) — see the ✗ and ! lines above." >&2
    exit 1
  fi
  (( APPLY )) && echo "Done." || echo "Dry run complete. Re-run with --apply to write."
}
