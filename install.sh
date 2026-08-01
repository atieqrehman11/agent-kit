#!/usr/bin/env bash
# Install the Claude skills in this repo into a target .claude directory.
#
# Usage:
#   ./install.sh                          # asks where to install, then generates PROFILE.md
#   ./install.sh ~/.claude                # install for all projects on this machine
#   ./install.sh /path/to/project         # install into that project's .claude
#   ./install.sh ~/.claude --no-profile   # install only; set up the profile later
#   ./install.sh --help
#
# Copies the skills (a snapshot) and rewrites the __SKILL_DIR__ path token — in every
# skill, to that skill's installed directory — so the slash commands find their scripts.
# Then generates the shared profile sheet: the org/project values (branding, team, CI/CD,
# policies, engine/tool paths) skills bake into what they generate. Fill it in and apply
# with /scaffold:profile (all optional).
#
# Each skill is REPLACED, not merged, so a file deleted from the repo does not linger as a
# stale slash command. Anything hand-edited inside an installed skill directory is lost —
# edit the repo and re-run instead.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# The header comment above IS the help text — printed whole, so editing one keeps both true.
usage() { awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; }

# ── Presentation ─────────────────────────────────────────────────────────────
if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  B=$'\033[1m'; DIM=$'\033[2m'; GRN=$'\033[32m'; YLW=$'\033[33m'
  RED=$'\033[31m'; CYA=$'\033[36m'; R=$'\033[0m'; TTY=1
else
  B=''; DIM=''; GRN=''; YLW=''; RED=''; CYA=''; R=''; TTY=0
fi
LINE="──────────────────────────────────────────────────────────────────────"

STEP=0
step() {  # step <title>
  STEP=$((STEP + 1))
  printf '\n  %s[%d/%d]%s  %s%s%s\n' "$DIM" "$STEP" "$TOTAL" "$R" "$B" "$1" "$R"
}
ok()   { printf '         %s✓%s  %s\n' "$GRN" "$R" "$1"; }
note() { printf '         %s·%s  %s\n' "$DIM" "$R" "$1"; }
warn() { printf '         %s!%s  %s\n' "$YLW" "$R" "$1"; }
die()  { printf '\n         %s✗  %s%s\n\n' "$RED" "$1" "$R" >&2; exit 1; }
# A live line while a unit of work runs; replaced by its result on a TTY.
busy() { [[ $TTY -eq 1 ]] && printf '         %s○  %s%s' "$DIM" "$1" "$R"; return 0; }
clear_busy() { [[ $TTY -eq 1 ]] && printf '\r\033[2K'; return 0; }

# ── Arguments ────────────────────────────────────────────────────────────────
TARGET=""
COLLECT_PROFILE=1
for arg in "$@"; do
  case "$arg" in
    --no-profile) COLLECT_PROFILE=0 ;;
    -h|--help)    usage; exit 0 ;;
    -*)           printf 'unknown option: %s\n\n' "$arg" >&2; usage >&2; exit 2 ;;
    *)            [[ -n "$TARGET" ]] && { echo "error: more than one target given" >&2; exit 2; }
                  TARGET="$arg" ;;
  esac
done

# ── What is about to be installed ────────────────────────────────────────────
shopt -s nullglob
SKILLS=()
for d in "$REPO_ROOT"/commands/*/; do SKILLS+=("$(basename "$d")"); done
[[ ${#SKILLS[@]} -eq 0 ]] && die "no skills found in $REPO_ROOT/commands/"

N_CMD=0
for n in "${SKILLS[@]}"; do
  for md in "$REPO_ROOT/commands/$n"/*.md; do
    [[ "$(basename "$md")" == "README.md" ]] && continue
    N_CMD=$((N_CMD + 1))
  done
done

VERSION="$(git -C "$REPO_ROOT" log -1 --format='%h  %cs' 2>/dev/null || echo 'not a git checkout')"
DIRTY=""
git -C "$REPO_ROOT" diff --quiet 2>/dev/null || DIRTY=" (uncommitted changes included)"

printf '\n  %s%s%s\n' "$B" "Claude Skills" "$R"
printf '  %s%s%s\n' "$DIM" "$LINE" "$R"
printf '  %-10s %s%s\n' "source" "$REPO_ROOT" ""
printf '  %-10s %s%s%s\n' "version" "$VERSION" "$YLW$DIRTY" "$R"
printf '  %-10s %s%d skills · %d commands%s\n' "contents" "$CYA" "${#SKILLS[@]}" "$N_CMD" "$R"

# ── Resolve the target .claude directory ─────────────────────────────────────
if [[ -z "$TARGET" ]]; then
  printf '\n'
  read -r -p "  Install into which .claude dir (or a project root)? [~/.claude] " TARGET
  TARGET="${TARGET:-$HOME/.claude}"
fi
TARGET="${TARGET/#\~/$HOME}"                 # expand a leading ~
# Accept either a .claude dir directly, or a project root (append /.claude).
[[ "$(basename "$TARGET")" != ".claude" ]] && TARGET="$TARGET/.claude"
printf '  %-10s %s%s%s\n' "target" "$B" "$TARGET" "$R"

TOTAL=4
PROFILE_PY_SRC="$REPO_ROOT/commands/scaffold/profile.py"
[[ "$COLLECT_PROFILE" -eq 1 && -f "$PROFILE_PY_SRC" ]] && TOTAL=5

# ── 1. Prerequisites ─────────────────────────────────────────────────────────
step "Checking prerequisites"

command -v python3 >/dev/null 2>&1 \
  || die "python3 is required (it rewrites the script paths and runs the skills)"
ok "python3 $(python3 -V 2>&1 | awk '{print $2}')  ·  bash ${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}"

mkdir -p "$TARGET/commands" 2>/dev/null || die "cannot create $TARGET/commands — check permissions"
[[ -w "$TARGET/commands" ]] || die "$TARGET/commands is not writable"

# Installing into this repo would delete the sources, since each skill is replaced.
if [[ "$(cd "$TARGET/commands" && pwd)" == "$REPO_ROOT/commands" ]]; then
  die "refusing to install over the source repo — pick a different target"
fi
ok "target writable"

# Optional at install time, needed when a skill actually runs. Warn, never block.
if python3 -c 'import openpyxl' 2>/dev/null; then
  ok "openpyxl present  $DIM(/plan:release scheduler and validator)$R"
else
  warn "openpyxl missing — /plan:release cannot schedule until:  pip install openpyxl"
fi
if python3 "$REPO_ROOT/commands/diagram/render.py" --which >/dev/null 2>&1; then
  ok "draw.io found     $DIM($(python3 "$REPO_ROOT/commands/diagram/render.py" --which 2>/dev/null | tail -1))$R"
else
  warn "draw.io not found — /diagram:build cannot render to PNG until it is installed"
fi

# ── 2. Copy each skill under commands/ ───────────────────────────────────────
step "Installing skills"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
installed=()
N_FILES=0
N_STALE=0

for name in "${SKILLS[@]}"; do
  skill_dir="$REPO_ROOT/commands/$name/"
  dest="$TARGET/commands/$name"
  busy "$name"

  verb="installed"
  if [[ -d "$dest" ]]; then
    verb="updated"
    (cd "$dest" && find . -type f 2>/dev/null | sort) > "$TMP/before" || : > "$TMP/before"
  else
    : > "$TMP/before"
  fi

  # Replace rather than merge, so a file removed from the repo does not linger here.
  rm -rf "$dest"
  mkdir -p "$dest"
  cp -R "$skill_dir." "$dest/"

  # Never ship caches or OS cruft — including the nested ones under templates/.
  find "$dest" \( -name '__pycache__' -o -name '.ruff_cache' \) -type d -prune \
       -exec rm -rf {} + 2>/dev/null || true
  find "$dest" -name '.DS_Store' -delete 2>/dev/null || true
  # A skill's own README documents the repo, not a command — and every *.md at a skill's
  # root registers as a slash command. Leave it out of the install.
  rm -f "$dest/README.md"

  (cd "$dest" && find . -type f | sort) > "$TMP/after"
  files=$(wc -l < "$TMP/after" | tr -d ' ')
  # grep -c exits 1 on zero matches; keep the count numeric under pipefail.
  stale=$(comm -23 "$TMP/before" "$TMP/after" | grep -c '.' || true)
  stale="${stale:-0}"
  cmds=0
  for md in "$dest"/*.md; do cmds=$((cmds + 1)); done
  N_FILES=$((N_FILES + files))
  N_STALE=$((N_STALE + stale))

  clear_busy
  extra=""
  [[ "$stale" -gt 0 ]] && extra="  ${YLW}${stale} stale file(s) removed${R}"
  printf '         %s✓%s  %-10s %s%2d command(s) · %2d files · %s%s%s\n' \
         "$GRN" "$R" "$name" "$DIM" "$cmds" "$files" "$verb" "$R" "$extra"
  installed+=("$name")
done

# ── 3. Rewrite the install-time path token ───────────────────────────────────
step "Wiring script paths"
busy "rewriting __SKILL_DIR__"

REWROTE="$(ROOT="$TARGET/commands" NAMES="$(printf '%s\n' "${installed[@]}")" python3 - <<'PY'
import os

root = os.environ["ROOT"]
changed = 0
for name in os.environ["NAMES"].split():
    dest = os.path.join(root, name)
    for dirpath, dirs, files in os.walk(dest):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".ruff_cache")]
        for n in files:
            p = os.path.join(dirpath, n)
            try:
                with open(p, encoding="utf-8") as fh:
                    s = fh.read()
            except (UnicodeDecodeError, IsADirectoryError, PermissionError):
                continue
            # __SKILL_DIR__ is the token every skill uses; __SCAFFOLD_DIR__ is the
            # pre-rename alias, kept so an older skill copy still installs correctly.
            t = s.replace("__SKILL_DIR__", dest).replace("__SCAFFOLD_DIR__", dest)
            if t != s:
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(t)
                changed += 1
print(changed)
PY
)"
clear_busy
ok "$REWROTE file(s) now point at their installed directory"

cat > "$TARGET/commands/.claude-skills-install" <<EOF
source   $REPO_ROOT
version  $VERSION$DIRTY
date     $(date -u +%Y-%m-%dT%H:%M:%SZ)
skills   ${installed[*]}
EOF
note "receipt written to commands/.claude-skills-install"

# ── 4. Verify ────────────────────────────────────────────────────────────────
step "Verifying"

CMD_LIST=()
for n in "${installed[@]}"; do
  for md in "$TARGET/commands/$n"/*.md; do CMD_LIST+=("/$n:$(basename "$md" .md)"); done
done
if [[ ${#CMD_LIST[@]} -eq "$N_CMD" ]]; then
  ok "${#CMD_LIST[@]} command(s) registered"
else
  warn "${#CMD_LIST[@]} command(s) registered, expected $N_CMD"
fi

# Compile without writing bytecode into the installed tree.
BAD="$(python3 - "$TARGET/commands"/*/*.py <<'PY'
import sys

bad = []
for p in sys.argv[1:]:
    try:
        with open(p, encoding="utf-8") as fh:
            compile(fh.read(), p, "exec")
    except SyntaxError as e:
        bad.append(f"{p}:{e.lineno} {e.msg}")
print(len(sys.argv) - 1)
for b in bad:
    print("BAD " + b)
PY
)"
N_PY="$(printf '%s\n' "$BAD" | head -1)"
if printf '%s\n' "$BAD" | grep -q '^BAD '; then
  printf '%s\n' "$BAD" | sed -n 's/^BAD /         '"$RED"'✗'"$R"'  /p'
  die "a skill script does not compile — fix it in the repo and re-run"
fi
ok "$N_PY python script(s) compile"

# grep exits 1 when it finds nothing, which is the good case — do not let pipefail kill it.
LEFT="$(grep -rl '__SKILL_DIR__\|__SCAFFOLD_DIR__' "$TARGET/commands" 2>/dev/null || true)"
LEFT="$(printf '%s' "$LEFT" | grep -c '.' || true)"
LEFT="${LEFT:-0}"
if [[ "$LEFT" -eq 0 ]]; then
  ok "no unresolved path tokens"
else
  warn "$LEFT file(s) still contain an unresolved path token"
fi

# ── 5. Generate the org/project profile sheet ────────────────────────────────
PROFILE_PY="$TARGET/commands/scaffold/profile.py"
PROFILE_SHEET="$TARGET/scaffold-profile.md"
PROFILE_READY=0
if [[ "$COLLECT_PROFILE" -eq 1 && -f "$PROFILE_PY" ]]; then
  step "Generating the profile sheet"
  busy "scaffold-profile.md"
  python3 "$PROFILE_PY" --generate >/dev/null
  clear_busy
  PROFILE_READY=1
  ok "$PROFILE_SHEET"
  note "org/project values skills bake into what they generate — all optional"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
printf '\n  %s%s%s\n' "$DIM" "$LINE" "$R"
printf '  %s✓  Installed%s  %s%d skills · %d commands · %d files%s\n' \
       "$GRN" "$R" "$DIM" "${#installed[@]}" "${#CMD_LIST[@]}" "$N_FILES" "$R"
[[ "$N_STALE" -gt 0 ]] && printf '     %s%d stale file(s) from a previous install were removed%s\n' \
                                  "$DIM" "$N_STALE" "$R"
printf '  %s%s%s\n' "$DIM" "$LINE" "$R"

printf '\n  %sCommands%s %s(in a Claude Code session using %s)%s\n' \
       "$B" "$R" "$DIM" "$TARGET" "$R"
# Derived from what was installed — each top-level <skill>/<cmd>.md is /<skill>:<cmd>,
# described by its first markdown heading. Nothing about the skill set is hardcoded here.
for n in "${installed[@]}"; do
  for md in "$TARGET/commands/$n"/*.md; do
    cmd="$(basename "$md" .md)"
    desc="$(grep -m1 '^# ' "$md" 2>/dev/null || true)"
    desc="${desc#\# }"
    [[ ${#desc} -gt 62 ]] && desc="${desc:0:59}..."
    printf '    %s%-22s%s %s%s%s\n' "$CYA" "/$n:$cmd" "$R" "$DIM" "$desc" "$R"
  done
done

printf '\n  %sNext steps%s\n' "$B" "$R"
if [[ "$PROFILE_READY" -eq 1 ]]; then
  printf '    1. Fill in the shared org/project values (all optional):\n'
  printf '         %s\n' "$PROFILE_SHEET"
  printf '       then apply them:   %s/scaffold:profile%s\n' "$CYA" "$R"
else
  printf '    1. Generate the shared profile sheet when ready:\n'
  printf '         python3 %s --generate\n' "$PROFILE_PY"
  printf '       fill it in, then:  %s/scaffold:profile%s\n' "$CYA" "$R"
fi
printf '    2. (optional) Choose where scaffolded repos are written — set output_dir in\n'
printf '       the profile sheet above, or export an env var (default: current directory):\n'
printf '         export SCAFFOLD_OUTPUT_DIR="$HOME/repos"\n'
printf '    3. Scaffold your first repo:   %s/scaffold:new%s\n' "$CYA" "$R"
printf '\n  %s%s%s\n\n' "$DIM" "$LINE" "$R"
