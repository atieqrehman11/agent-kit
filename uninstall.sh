#!/usr/bin/env bash
# Remove the Claude skills this repo installed from a target .claude directory.
#
# Usage:
#   ./uninstall.sh                        # asks which .claude dir, shows a plan, confirms
#   ./uninstall.sh ~/.claude              # plan + confirm for that install
#   ./uninstall.sh ~/.claude --dry-run    # show what would go; change nothing
#   ./uninstall.sh ~/.claude --yes        # no prompt (for scripts and CI)
#   ./uninstall.sh ~/.claude --profile    # also delete the filled-in profile sheet/json
#   ./uninstall.sh ~/.claude --all --yes  # skills + profile + receipt, unattended
#   ./uninstall.sh --caches               # tidy this repo: __pycache__, .ruff_cache, .DS_Store
#   ./uninstall.sh --help
#
# It removes ONLY the skill directories this repo installed, read from the install receipt
# at <target>/commands/.claude-skills-install. Commands you installed from anywhere else are
# listed and left alone. Nothing is deleted before you see the plan.
#
# The profile sheet holds values you typed in by hand, so it is KEPT unless you pass
# --profile or --all.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
RECEIPT_NAME=".claude-skills-install"

# The header comment above IS the help text — printed whole, so editing one keeps both true.
usage() { awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; }

# ── Presentation (matches install.sh) ────────────────────────────────────────
if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  B=$'\033[1m'; DIM=$'\033[2m'; GRN=$'\033[32m'; YLW=$'\033[33m'
  RED=$'\033[31m'; CYA=$'\033[36m'; R=$'\033[0m'
else
  B=''; DIM=''; GRN=''; YLW=''; RED=''; CYA=''; R=''
fi
LINE="──────────────────────────────────────────────────────────────────────"

STEP=0
step() { STEP=$((STEP + 1)); printf '\n  %s[%d/%d]%s  %s%s%s\n' "$DIM" "$STEP" "$TOTAL" "$R" "$B" "$1" "$R"; }
ok()   { printf '         %s✓%s  %s\n' "$GRN" "$R" "$1"; }
note() { printf '         %s·%s  %s\n' "$DIM" "$R" "$1"; }
warn() { printf '         %s!%s  %s\n' "$YLW" "$R" "$1"; }
gone() { printf '         %s✗%s  %s\n' "$RED" "$R" "$1"; }
die()  { printf '\n         %s✗  %s%s\n\n' "$RED" "$1" "$R" >&2; exit 1; }

# ── Arguments ────────────────────────────────────────────────────────────────
TARGET=""; DRY=0; ASSUME_YES=0; DO_PROFILE=0; DO_CACHES=0; ONLY_CACHES=0
for arg in "$@"; do
  case "$arg" in
    -n|--dry-run) DRY=1 ;;
    -y|--yes)     ASSUME_YES=1 ;;
    --profile)    DO_PROFILE=1 ;;
    --all)        DO_PROFILE=1 ;;
    --caches)     DO_CACHES=1 ;;
    -h|--help)    usage; exit 0 ;;
    -*)           printf 'unknown option: %s\n\n' "$arg" >&2; usage >&2; exit 2 ;;
    *)            [[ -n "$TARGET" ]] && { echo "error: more than one target given" >&2; exit 2; }
                  TARGET="$arg" ;;
  esac
done
# --caches on its own is a repo tidy-up, not an uninstall.
[[ "$DO_CACHES" -eq 1 && -z "$TARGET" ]] && ONLY_CACHES=1

printf '\n  %s%s%s\n' "$B" "Claude Skills — uninstall" "$R"
printf '  %s%s%s\n' "$DIM" "$LINE" "$R"

# ── Repo tidy-up mode ────────────────────────────────────────────────────────
clean_repo_caches() {
  local n
  n="$(find "$REPO_ROOT" \( -name '__pycache__' -o -name '.ruff_cache' \) -type d 2>/dev/null | wc -l | tr -d ' ')"
  local d
  d="$(find "$REPO_ROOT" -name '.DS_Store' -type f 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$DRY" -eq 1 ]]; then
    note "would remove $n cache dir(s) and $d .DS_Store file(s) under $REPO_ROOT"
    return 0
  fi
  find "$REPO_ROOT" \( -name '__pycache__' -o -name '.ruff_cache' \) -type d -prune \
       -exec rm -rf {} + 2>/dev/null || true
  find "$REPO_ROOT" -name '.DS_Store' -type f -delete 2>/dev/null || true
  ok "removed $n cache dir(s) and $d .DS_Store file(s) from the repo"
}

if [[ "$ONLY_CACHES" -eq 1 ]]; then
  TOTAL=1
  printf '  %-10s %s\n' "repo" "$REPO_ROOT"
  step "Tidying the repo working tree"
  clean_repo_caches
  printf '\n  %s%s%s\n\n' "$DIM" "$LINE" "$R"
  exit 0
fi

# ── Resolve the target .claude directory ─────────────────────────────────────
printf '  %-10s %s\n' "source" "$REPO_ROOT"
if [[ -z "$TARGET" ]]; then
  printf '\n'
  read -r -p "  Uninstall from which .claude dir (or a project root)? [~/.claude] " TARGET
  TARGET="${TARGET:-$HOME/.claude}"
fi
TARGET="${TARGET/#\~/$HOME}"
[[ "$(basename "$TARGET")" != ".claude" ]] && TARGET="$TARGET/.claude"
printf '  %-10s %s%s%s\n' "target" "$B" "$TARGET" "$R"

CMD_DIR="$TARGET/commands"
[[ -d "$CMD_DIR" ]] || die "$CMD_DIR does not exist — nothing installed there"
# Never operate on the source repo: these skills are the originals, not a copy.
if [[ "$(cd "$CMD_DIR" && pwd)" == "$REPO_ROOT/commands" ]]; then
  die "that is the source repo, not an install — refusing to delete the originals"
fi

TOTAL=2
[[ "$DO_CACHES" -eq 1 ]] && TOTAL=3

# ── 1. Plan ──────────────────────────────────────────────────────────────────
step "Planning"

RECEIPT="$CMD_DIR/$RECEIPT_NAME"
SKILLS=""
if [[ -f "$RECEIPT" ]]; then
  SKILLS="$(awk '$1 == "skills" { $1 = ""; print }' "$RECEIPT")"
  ok "receipt found"
  while IFS= read -r l; do [[ -n "$l" ]] && note "$l"; done < "$RECEIPT"
else
  # No receipt (installed by an older install.sh). Infer from what this repo ships, so we
  # still never touch a command directory this repo does not own.
  shopt -s nullglob
  for d in "$REPO_ROOT"/commands/*/; do SKILLS="$SKILLS $(basename "$d")"; done
  warn "no receipt at commands/$RECEIPT_NAME — inferring from what this repo ships"
fi

REMOVE=""; MISSING=""; N_FILES=0
for name in $SKILLS; do
  d="$CMD_DIR/$name"
  if [[ -d "$d" || -L "$d" ]]; then
    REMOVE="$REMOVE $name"
    if [[ -L "$d" ]]; then
      f=0
    else
      f="$(find "$d" -type f 2>/dev/null | wc -l | tr -d ' ')"
    fi
    N_FILES=$((N_FILES + f))
  else
    MISSING="$MISSING $name"
  fi
done

# Anything else under commands/ belongs to someone else. Say so explicitly.
FOREIGN=""
shopt -s nullglob
for d in "$CMD_DIR"/*/; do
  n="$(basename "$d")"
  case " $SKILLS " in *" $n "*) ;; *) FOREIGN="$FOREIGN $n" ;; esac
done

PROFILE_MD="$TARGET/scaffold-profile.md"
PROFILE_JSON="$TARGET/scaffold-profile.json"

printf '\n'
if [[ -z "$REMOVE" ]]; then
  warn "no skills from this repo are installed at that target"
else
  printf '         %sWill remove%s\n' "$B" "$R"
  for name in $REMOVE; do
    d="$CMD_DIR/$name"
    if [[ -L "$d" ]]; then
      printf '           %s✗%s  %-10s %ssymlink%s\n' "$RED" "$R" "$name" "$DIM" "$R"
    else
      f="$(find "$d" -type f 2>/dev/null | wc -l | tr -d ' ')"
      c=0; for md in "$d"/*.md; do c=$((c + 1)); done
      printf '           %s✗%s  %-10s %s%2d command(s) · %2d files%s\n' \
             "$RED" "$R" "$name" "$DIM" "$c" "$f" "$R"
    fi
  done
  [[ -f "$RECEIPT" ]] && printf '           %s✗%s  %-10s %scommands/%s%s\n' \
                                "$RED" "$R" "receipt" "$DIM" "$RECEIPT_NAME" "$R"
fi

if [[ "$DO_PROFILE" -eq 1 ]]; then
  for p in "$PROFILE_MD" "$PROFILE_JSON"; do
    [[ -e "$p" ]] && printf '           %s✗%s  %-10s %s%s%s\n' \
                            "$RED" "$R" "profile" "$DIM" "$(basename "$p")" "$R"
  done
elif [[ -e "$PROFILE_MD" || -e "$PROFILE_JSON" ]]; then
  printf '\n         %sKept%s  %s(hand-entered values — pass --profile to delete)%s\n' \
         "$B" "$R" "$DIM" "$R"
  for p in "$PROFILE_MD" "$PROFILE_JSON"; do
    [[ -e "$p" ]] && printf '           %s·%s  %s\n' "$DIM" "$R" "$p"
  done
fi

if [[ -n "$FOREIGN" ]]; then
  printf '\n         %sLeft alone%s  %s(not installed by this repo)%s\n' "$B" "$R" "$DIM" "$R"
  for n in $FOREIGN; do printf '           %s·%s  %s\n' "$DIM" "$R" "$n"; done
fi
[[ -n "$MISSING" ]] && { printf '\n'; note "already gone:$MISSING"; }

if [[ -z "$REMOVE" && "$DO_PROFILE" -eq 0 && "$DO_CACHES" -eq 0 ]]; then
  printf '\n  %s%s%s\n\n' "$DIM" "$LINE" "$R"
  exit 0
fi

if [[ "$DRY" -eq 1 ]]; then
  printf '\n  %s%s%s\n' "$DIM" "$LINE" "$R"
  printf '  %s·  Dry run — nothing was changed.%s Re-run without --dry-run to apply.\n' "$DIM" "$R"
  printf '  %s%s%s\n\n' "$DIM" "$LINE" "$R"
  exit 0
fi

# ── 2. Confirm ───────────────────────────────────────────────────────────────
if [[ "$ASSUME_YES" -eq 0 ]]; then
  [[ -t 0 ]] || die "not a terminal and --yes was not passed — refusing to delete unprompted"
  printf '\n'
  read -r -p "  Remove the items marked ✗ above? [y/N] " reply
  case "$reply" in
    y|Y|yes|YES) ;;
    *) printf '\n  %s·  Cancelled — nothing was changed.%s\n\n' "$DIM" "$R"; exit 0 ;;
  esac
fi

# ── 3. Remove ────────────────────────────────────────────────────────────────
step "Removing"

# Every path must be a direct child of the resolved commands dir. Cheap insurance against a
# malformed receipt or a name with a slash in it.
safe_rm_skill() {
  local name="$1" d="$CMD_DIR/$1"
  case "$name" in ""|*/*|.|..) die "refusing to remove a suspicious skill name: '$name'" ;; esac
  [[ -e "$d" || -L "$d" ]] || return 0
  rm -rf "$d"
  gone "commands/$name"
}
for name in $REMOVE; do safe_rm_skill "$name"; done
[[ -f "$RECEIPT" ]] && { rm -f "$RECEIPT"; gone "commands/$RECEIPT_NAME"; }

if [[ "$DO_PROFILE" -eq 1 ]]; then
  for p in "$PROFILE_MD" "$PROFILE_JSON"; do
    [[ -e "$p" ]] && { rm -f "$p"; gone "$(basename "$p")"; }
  done
fi

# An empty commands/ left behind is clutter; a non-empty one belongs to someone else.
if [[ -d "$CMD_DIR" ]] && [[ -z "$(ls -A "$CMD_DIR" 2>/dev/null)" ]]; then
  rmdir "$CMD_DIR" && gone "commands/ (now empty)"
fi

if [[ "$DO_CACHES" -eq 1 ]]; then
  step "Tidying the repo working tree"
  clean_repo_caches
fi

# ── Summary ──────────────────────────────────────────────────────────────────
n_removed=0; for _ in $REMOVE; do n_removed=$((n_removed + 1)); done
printf '\n  %s%s%s\n' "$DIM" "$LINE" "$R"
printf '  %s✓  Uninstalled%s  %s%d skill(s) · %d files removed%s\n' \
       "$GRN" "$R" "$DIM" "$n_removed" "$N_FILES" "$R"
if [[ -n "$FOREIGN" ]]; then
  printf '     %s%s left in place%s\n' "$DIM" "$(echo $FOREIGN | tr ' ' ',')" "$R"
fi
printf '  %s%s%s\n' "$DIM" "$LINE" "$R"
printf '\n  Reinstall any time:   %s./install.sh %s%s\n' "$CYA" "$TARGET" "$R"
printf '  %sSlash commands disappear from a Claude Code session once it is restarted.%s\n\n' "$DIM" "$R"
