#!/usr/bin/env bash
# Install the Claude skills in this repo into a target .claude directory.
#
# Usage:
#   ./install.sh                       # asks where to install, then generates PROFILE.md
#   ./install.sh ~/.claude             # install for all projects on this machine
#   ./install.sh /path/to/project      # install into that project's .claude
#   ./install.sh ~/.claude --no-profile   # install only; set up the profile later
#
# Copies the skills (a snapshot) and rewrites the __SKILL_DIR__ path token — in every
# skill, to that skill's installed directory — so the slash commands find their scripts.
# Then generates the shared profile sheet: the org/project values (branding, team, CI/CD,
# policies, engine/tool paths) skills bake into what they generate. Fill it in and apply
# with /scaffold:profile (all optional).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Resolve the target .claude directory ─────────────────────────────────────
TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  read -r -p "Install into which .claude dir (or a project root)? [~/.claude] " TARGET
  TARGET="${TARGET:-$HOME/.claude}"
fi
TARGET="${TARGET/#\~/$HOME}"                 # expand a leading ~
# Accept either a .claude dir directly, or a project root (append /.claude).
if [[ "$(basename "$TARGET")" != ".claude" ]]; then
  TARGET="$TARGET/.claude"
fi
mkdir -p "$TARGET/commands"

COLLECT_PROFILE=1
[[ "${2:-}" == "--no-profile" ]] && COLLECT_PROFILE=0

# ── Copy each skill under commands/ ──────────────────────────────────────────
installed=()
for skill_dir in "$REPO_ROOT"/commands/*/; do
  name="$(basename "$skill_dir")"
  dest="$TARGET/commands/$name"
  mkdir -p "$dest"
  cp -R "$skill_dir." "$dest/"
  # Never ship caches.
  find "$dest" -name '.DS_Store' -delete 2>/dev/null || true
  rm -rf "$dest/.ruff_cache" "$dest/__pycache__" 2>/dev/null || true
  # The skill's own README documents the repo, not a command — and every *.md at a
  # skill's root registers as a slash command. Leave it out of the install.
  rm -f "$dest/README.md"
  # Rewrite the install-time path token across every text file.
  DEST="$dest" python3 - <<'PY'
import os
dest = os.environ["DEST"]
for root, dirs, files in os.walk(dest):
    dirs[:] = [d for d in dirs if d not in ("__pycache__", ".ruff_cache")]
    for n in files:
        p = os.path.join(root, n)
        try:
            with open(p, encoding="utf-8") as fh:
                s = fh.read()
        except (UnicodeDecodeError, IsADirectoryError):
            continue
        # __SKILL_DIR__ is the token every skill uses; __SCAFFOLD_DIR__ is the
        # pre-rename alias, kept so an older skill copy still installs correctly.
        t = s.replace("__SKILL_DIR__", dest).replace("__SCAFFOLD_DIR__", dest)
        if t != s:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(t)
PY
  installed+=("$name")
done

# ── Generate the org/project profile sheet ───────────────────────────────────
PROFILE_PY="$TARGET/commands/scaffold/profile.py"
PROFILE_SHEET="$TARGET/scaffold-profile.md"
PROFILE_READY=0
if [[ "$COLLECT_PROFILE" -eq 1 && -f "$PROFILE_PY" ]]; then
  python3 "$PROFILE_PY" --generate >/dev/null
  PROFILE_READY=1
fi

# ── Summary ──────────────────────────────────────────────────────────────────
rule() { printf '  %s\n' "──────────────────────────────────────────────────────────────────"; }

echo
rule
echo "  ✓  Claude skills installed"
rule
echo
echo "  Created"
echo "    Commands        $TARGET/commands/"
for n in "${installed[@]}"; do
  echo "                      • $n"
done
if [[ "$PROFILE_READY" -eq 1 ]]; then
  echo "    Profile sheet   $PROFILE_SHEET"
fi
echo
echo "  Commands available (in a Claude Code session using $TARGET)"
# Derived from what was installed — each top-level <skill>/<cmd>.md is /<skill>:<cmd>,
# described by its first markdown heading. Nothing about the skill set is hardcoded here.
for n in "${installed[@]}"; do
  for md in "$TARGET/commands/$n"/*.md; do
    [[ -e "$md" ]] || continue
    cmd="$(basename "$md" .md)"
    desc="$(grep -m1 '^# ' "$md" 2>/dev/null || true)"
    desc="${desc#\# }"
    printf '    %-22s %s\n' "/$n:$cmd" "$desc"
  done
done
echo
echo "  Next steps"
if [[ "$PROFILE_READY" -eq 1 ]]; then
  echo "    1. Fill in the shared org/project values (all optional):"
  echo "         $PROFILE_SHEET"
  echo "       then apply them:   /scaffold:profile"
else
  echo "    1. Generate the shared profile sheet when ready:"
  echo "         python3 $PROFILE_PY --generate"
  echo "       fill it in, then:  /scaffold:profile"
fi
echo "    2. (optional) Choose where scaffolded repos are written — set output_dir in"
echo "       the profile sheet above, or export an env var (default: current directory):"
echo "         export SCAFFOLD_OUTPUT_DIR=\"\$HOME/repos\""
echo "    3. Scaffold your first repo:   /scaffold:new"
echo
rule
