#!/usr/bin/env bash
# PostToolUse (Write|Edit|MultiEdit): auto-format / lint-fix the file just written,
# so code is standardized without hand-cleanup. Self-adapting and non-breaking:
# it uses the first available formatter and stays completely silent (no-op) when
# none is installed, so it is safe to keep wired even in repos without tooling.
#
# Python (.py):            ruff format + ruff check --fix   (repo .venv → global → python -m ruff)
# JS/TS/React (.jsx/.tsx): prettier --write + eslint --fix  (repo node_modules/.bin only; no network fetch)
#
# Resolution walks up from the edited file to find repo-local tooling first, so each
# repo's own config/version wins.

f="$(jq -r '.tool_response.filePath // .tool_input.file_path // empty' 2>/dev/null)"
[ -z "$f" ] || [ ! -f "$f" ] && exit 0

# Walk up from the file's directory looking for a repo-local binary at $1.
find_up() {
  local rel="$1" dir; dir="$(dirname "$f")"
  while [ "$dir" != "/" ]; do
    [ -x "$dir/$rel" ] && { echo "$dir/$rel"; return 0; }
    dir="$(dirname "$dir")"
  done
  return 1
}

case "$f" in
  *.py)
    ruff="$(find_up .venv/bin/ruff || command -v ruff || true)"
    if [ -n "$ruff" ]; then
      "$ruff" format "$f" >/dev/null 2>&1
      "$ruff" check --fix "$f" >/dev/null 2>&1
    elif python3 -c 'import ruff' >/dev/null 2>&1; then
      python3 -m ruff format "$f" >/dev/null 2>&1
      python3 -m ruff check --fix "$f" >/dev/null 2>&1
    fi
    ;;
  *.js|*.jsx|*.ts|*.tsx|*.mjs|*.cjs)
    prettier="$(find_up node_modules/.bin/prettier || true)"
    [ -n "$prettier" ] && "$prettier" --write "$f" >/dev/null 2>&1
    eslint="$(find_up node_modules/.bin/eslint || true)"
    [ -n "$eslint" ] && "$eslint" --fix "$f" >/dev/null 2>&1
    ;;
esac
exit 0
