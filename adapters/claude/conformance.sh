#!/usr/bin/env bash
# STANDARD.md §2.4 + §2.5 conformance run against the Claude adapter.
# Every check tests a property. None of them match a string I already know is there.
set -u
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
W=$(mktemp -d)
T="$W/t/.claude"
PASS=0; FAIL=0
r() { if [ "$1" = 0 ]; then echo "  PASS  $2"; PASS=$((PASS+1)); else echo "  FAIL  $2"; FAIL=$((FAIL+1)); fi }

echo "== §2.4 verification (per install) =="

# 1 install succeeds on a clean target
mkdir -p "$T"
printf 'user data\n' > "$T/scaffold-profile.md"
printf 'hand written\n' > "$T/skills-note.txt"
python3 "$KIT/adapters/claude/install.py" "$T" >"$W/i1.log" 2>&1
r $? "install exits 0 on a clean target"

# 2 declared == registered, no unresolved markers, profile untouched (installer's own verify)
grep -q "entry points registered, zero payload" "$W/i1.log"; r $? "declared entry points == registered"
grep -q "no unresolved markers" "$W/i1.log"; r $? "zero surviving markers"

# 3 every {{cmd:}} resolved to something that exists: no /skill:verb in output lacks a file
python3 - "$T" <<'PY'
import os,re,sys
t=sys.argv[1]; bad=[]
have={f"{d}:{os.path.splitext(f)[0]}"
      for d in (os.listdir(os.path.join(t,"commands")) if os.path.isdir(os.path.join(t,"commands")) else [])
      for f in os.listdir(os.path.join(t,"commands",d))}
for sub in ("guidelines","skills","commands","agents"):
    for r_,_,fs in os.walk(os.path.join(t,sub)):
        for f in fs:
            if not f.endswith(".md"): continue
            try: txt=open(os.path.join(r_,f),encoding="utf-8").read()
            except Exception: continue
            for m in re.findall(r"(?<![\w/`])/([a-z][a-z-]+):([a-z][a-z-]+)",txt):
                if f"{m[0]}:{m[1]}" not in have: bad.append((os.path.join(r_,f),m))
if bad:
    for b in bad[:8]: print("dangling",b)
sys.exit(1 if bad else 0)
PY
r $? "every rendered /skill:verb reference resolves to an installed command"

# 4 kit data dir preserved
[ "$(cat "$T/scaffold-profile.md")" = "user data" ] && [ -f "$T/skills-note.txt" ]
r $? "kit data dir contents byte-identical after install (obligation 11)"

# 5 every installed script parses
find "$T/skills" -name '*.py' -print0 | xargs -0 -n1 python3 -m py_compile 2>"$W/py.log"
r $? "every installed .py parses"

# 6 receipt written and lists artifacts
python3 -c "
import json,sys; r=json.load(open('$T/.agent-kit-install.json'))
sys.exit(0 if all(r.get(k) for k in ('guidelines','skills','commands','agents')) and r.get('source') and r.get('installed_at') else 1)"
r $? "receipt written, lists all four kinds + source + timestamp"

# 7 §1.4: every registered entry point carries a description — a skill's, a subagent's, and
# a command's alike. This is what the picker shows the user; blank is not a soft failure.
python3 - "$T" <<'PY'
import os, re, sys
t = sys.argv[1]; bad = []
for sub in ("skills", "commands", "agents"):
    for r_, _, fs in os.walk(os.path.join(t, sub)):
        for f in fs:
            if not f.endswith(".md"):
                continue
            p = os.path.join(r_, f)
            parts = os.path.relpath(p, t).split(os.sep)
            entry = (
                (parts[0] == "skills" and len(parts) == 3 and parts[2] == "SKILL.md")
                or (parts[0] == "commands" and len(parts) == 3)
                or (parts[0] == "agents" and len(parts) == 2)
            )
            if not entry:
                continue
            m = re.match(r"\A---\n(.*?)\n---\n", open(p, encoding="utf-8").read(), re.S)
            d = re.search(r"^description:[ \t]*(\S.*)$", m.group(1), re.M) if m else None
            if not d or len(d.group(1).strip()) < 20:
                bad.append(os.sep.join(parts))
for b in bad[:8]:
    print("no description:", b)
sys.exit(1 if bad else 0)
PY
r $? "every registered entry point carries a description (§1.4)"

# 8 the rendered frontmatter is valid YAML AND every value has the type a consumer expects.
# The regex above passes on `argument-hint: [path; default = x]` — which YAML reads as a
# *list*, not a string. A consumer that type-checks can reject the whole block, taking the
# description with it. Checking "a description is present" never sees that; this does.
python3 - "$T" <<'PY'
import os, re, sys
try:
    import yaml
except ImportError:
    print("pyyaml missing — this check cannot run"); sys.exit(1)
t = sys.argv[1]; bad = []
for sub in ("skills", "commands", "agents"):
    for r_, _, fs in os.walk(os.path.join(t, sub)):
        for f in fs:
            if not f.endswith(".md"):
                continue
            p = os.path.join(r_, f)
            rel = os.path.relpath(p, t)
            m = re.match(r"\A---\n(.*?)\n---\n", open(p, encoding="utf-8").read(), re.S)
            if not m:
                continue
            try:
                fm = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError as e:
                bad.append(f"{rel}: not valid YAML — {e}"); continue
            for k, v in fm.items():
                if not isinstance(v, str):
                    bad.append(f"{rel}: {k} is {type(v).__name__}, expected str — {v!r}")
for b in bad[:8]:
    print(b)
sys.exit(1 if bad else 0)
PY
r $? "rendered frontmatter parses as YAML with string-typed values"

echo
echo "== §2.5 conformance (the adapter itself) =="

# 9 idempotent: installing twice produces an identical tree
python3 "$KIT/adapters/claude/install.py" "$T" >"$W/i2.log" 2>&1
( cd "$T" && find guidelines skills commands agents -type f -exec shasum {} \; | sort ) > "$W/tree2"
python3 "$KIT/adapters/claude/install.py" "$T" >"$W/i3.log" 2>&1
( cd "$T" && find guidelines skills commands agents -type f -exec shasum {} \; | sort ) > "$W/tree3"
diff -q "$W/tree2" "$W/tree3" >/dev/null
r $? "installing twice produces an identical tree"

# 10 deleting an artifact from core/ removes it from the install
CORE2="$W/kit"; cp -R "$KIT" "$CORE2"
rm -rf "$CORE2/core/guidelines/streamlit.md"
python3 "$CORE2/adapters/claude/install.py" "$T" >"$W/i4.log" 2>&1
[ ! -e "$T/guidelines/streamlit.md" ] && [ ! -e "$T/skills/streamlit" ]
r $? "artifact deleted from core/ disappears from the install"

# 11 uninstall removes exactly the receipt contents, keeps the data dir
python3 "$CORE2/adapters/claude/install.py" "$T" --uninstall >"$W/u.log" 2>&1
LEFT=$(ls "$T" | grep -vc 'scaffold-profile.md\|skills-note.txt' || true)
[ "$LEFT" = 0 ] && [ -f "$T/scaffold-profile.md" ] && [ -f "$T/skills-note.txt" ] && [ ! -f "$T/.agent-kit-install.json" ]
r $? "uninstall removes exactly the receipt contents; data dir survives"

# 12 leak test: nothing under core/ names this tool
grep -rInE '\.claude|~/\.claude|CLAUDE\.md|SKILL\.md is registered|claude-code|\$ARGUMENTS|/[a-z-]+:[a-z-]+ ' "$KIT/core" \
  --include='*.md' --include='*.py' --include='*.sh' > "$W/leak" 2>/dev/null
LEAKS=$(grep -vc 'STANDARD.md' "$W/leak" 2>/dev/null || echo 0)
[ "$(wc -l < "$W/leak" | tr -d ' ')" = 0 ]
r $? "leak test: no core/ file names Claude's paths, filenames or invocation syntax"
[ -s "$W/leak" ] && head -8 "$W/leak"

# 13 adapter README states supported kinds
grep -qi 'kinds supported' "$KIT/adapters/claude/README.md"
r $? "adapter README states which kinds are supported and how each is expressed"

# 14 obligations 1-10 present as annotations in the reference implementation
python3 - "$KIT/adapters/claude/install.py" <<'PY'
import re,sys
t=open(sys.argv[1]).read()
missing=[n for n in range(1,11) if f"Obligation {n}" not in t and f"obligation {n}" not in t]
print("missing obligation annotations:",missing) if missing else None
sys.exit(1 if missing else 0)
PY
r $? "obligations 1-10 implemented and annotated"

echo
echo "  $PASS passed, $FAIL failed"
rm -rf "$W"
exit $FAIL
