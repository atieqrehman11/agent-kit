#!/usr/bin/env python3
"""Claude adapter — installs agent-kit's core/ into a .claude directory.

The reference implementation of STANDARD.md Part 2. Every obligation it satisfies is
numbered against that document; anything it needs that is not written there is a bug in
the standard, not a special case to add here.

    python3 adapters/claude/install.py [TARGET] [--dry-run] [--no-profile]

TARGET defaults to ~/.claude. It is also the kit data dir (obligation 11).

How each kind renders (STANDARD.md 2.2):

    guideline   <target>/guidelines/<name>.md        canonical copy, what __GUIDELINES_DIR__
                                                     points at; skills read it as a file
                <target>/skills/<name>/SKILL.md      model-invocable, applies_to folded into
                                                     the description. No slash command:
                                                     a constraint is not something you run.
    skill       <target>/skills/<name>/              SKILL.md + all payload; __SKILL_DIR__
                <target>/commands/<name>/<verb>.md   one user-invoked entry per command,
                                                     carrying its own description — that is
                                                     the line the slash-command picker shows
    subagent    <target>/agents/<name>.md            name + description frontmatter

A guideline is written twice on purpose: once in its canonical form for skills that read it
as a file, once in Claude's registration format. Both are generated, both are replaced
wholesale on every install, so neither can drift from core/.
"""

import argparse
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CORE = os.path.join(ROOT, "core")

C = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
B, DIM, GRN, YLW, RED, CYA, R = (
    ("\033[1m", "\033[2m", "\033[32m", "\033[33m", "\033[31m", "\033[36m", "\033[0m")
    if C
    else ("",) * 7
)
LINE = "─" * 70


def ok(m):
    print(f"         {GRN}✓{R}  {m}")


def note(m):
    print(f"         {DIM}·{R}  {m}")


def warn(m):
    print(f"         {YLW}!{R}  {m}")


def die(m):
    print(f"\n         {RED}✗  {m}{R}\n", file=sys.stderr)
    sys.exit(1)


STEP = [0]


def step(title, total):
    STEP[0] += 1
    print(f"\n  {DIM}[{STEP[0]}/{total}]{R}  {B}{title}{R}")


# ── Obligation 1: discover ──────────────────────────────────────────────────────

FM = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)


def parse(path):
    """Frontmatter dict (scalars, block scalars, list fields) plus the body.

    A block scalar (``description: >``) continues across every indented line, not just the
    first — getting that wrong truncates a description mid-sentence, and the description is
    the one thing a model has to select on.
    """
    m = FM.match(open(path, encoding="utf-8").read())
    if not m:
        return None, None
    raw, body = m.groups()
    fm, key, block = {}, None, False
    for line in raw.split("\n"):
        if block and (line.startswith("  ") or not line.strip()):
            if line.strip():
                fm[key] = (fm[key] + " " + line.strip()).strip()
            continue
        if re.match(r"^\s*-\s", line) and key:
            fm.setdefault(key + "__list", []).append(
                line.split("-", 1)[1].strip().strip("\"'")
            )
            continue
        kv = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            block = val in (">", "|")
            fm[key] = "" if block else val.strip("\"'")
    return fm, body


CONFORMANCE_SUFFIX = ".conformance.md"

# Any unresolved marker, not an enumeration of the ones we remember. §1.6: "an install with
# any surviving token is a failed install". Lowercase dunders (__init__, __file__) do not
# match, so payload scripts are unaffected.
MARKER_RE = re.compile(r"__[A-Z][A-Z0-9_]*__|\{\{cmd:[^}]*\}\}|\{\{args\}\}")


def conformance_src(name):
    """§1.2: the optional checklist sibling of a guideline. Payload, not an artifact."""
    p = f"{CORE}/guidelines/{name}{CONFORMANCE_SUFFIX}"
    return p if os.path.isfile(p) else None


def discover():
    arts = []
    for name in sorted(os.listdir(f"{CORE}/guidelines")):
        # A sibling is payload of the guideline beside it (§1.2). Discovering it as an
        # artifact would derive the name "service-structure.conformance", which matches
        # no frontmatter and no registration — obligation 2 would reject the install.
        if name.endswith(CONFORMANCE_SUFFIX):
            continue
        if name.endswith(".md"):
            arts.append(("guideline", name[:-3], f"{CORE}/guidelines/{name}"))
    for name in sorted(os.listdir(f"{CORE}/skills")):
        p = f"{CORE}/skills/{name}/SKILL.md"
        if os.path.isfile(p):
            arts.append(("skill", name, p))
    sub = f"{CORE}/subagents"
    for name in sorted(os.listdir(sub)) if os.path.isdir(sub) else []:
        if name.endswith(".md"):
            arts.append(("subagent", name[:-3], f"{sub}/{name}"))
    return arts


# ── Obligation 2: validate before writing a single byte ─────────────────────────


def check_fm(path, fm, name, kind, errs):
    """The frontmatter contract (§1.5), applied identically to every entry point.

    A command is an entry point too, and until this checked them the eight commands shipped
    with no description at all — so the one line a user reads in the picker was blank.
    """
    if fm is None:
        errs.append(f"{path}: no frontmatter")
        return
    if fm.get("name") != name:
        errs.append(
            f"{path}: name '{fm.get('name')}' does not match its path ('{name}')"
        )
    if fm.get("kind") != kind:
        errs.append(
            f"{path}: kind '{fm.get('kind')}' does not match its location ('{kind}')"
        )
    d = fm.get("description", "")
    if not d:
        errs.append(f"{path}: no description")
    elif d.endswith(".md") or d.startswith("@") or "/" in d.split()[0]:
        errs.append(f"{path}: description is a path, not prose")


def validate(arts):
    errs, entries = [], {}
    # §1.2: a sibling with no guideline beside it is a failed install, not a stray file —
    # same class as a dangling {{cmd:…}}: user-facing text pointing at nothing.
    have = {n for k, n, _ in arts if k == "guideline"}
    for f in sorted(os.listdir(f"{CORE}/guidelines")):
        if f.endswith(CONFORMANCE_SUFFIX) and f[: -len(CONFORMANCE_SUFFIX)] not in have:
            errs.append(f"{CORE}/guidelines/{f}: conformance sibling with no guideline")
    for kind, name, path in arts:
        fm, _ = parse(path)
        check_fm(path, fm, name, kind, errs)
        if kind == "skill":
            cdir = f"{CORE}/skills/{name}/commands"
            # §1.4: commands/*.md at depth 1, and nothing else — a stray file in here would
            # otherwise register as a verb named after its extension.
            verbs = (
                {f[:-3] for f in os.listdir(cdir) if f.endswith(".md")}
                if os.path.isdir(cdir)
                else set()
            )
            entries[name] = verbs
            for verb in sorted(verbs):
                cpath = os.path.join(cdir, f"{verb}.md")
                cfm, _ = parse(cpath)
                check_fm(cpath, cfm, verb, "command", errs)
    return errs, entries


def check_refs(entries):
    """Obligation 5: a {{cmd:...}} naming something that does not exist is a failed install."""
    bad = []
    for r, _, fs in os.walk(CORE):
        for f in fs:
            p = os.path.join(r, f)
            try:
                t = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            for m in re.finditer(r"\{\{cmd:([a-z-]+)(?::([a-z-]+))?\}\}", t):
                sk, vb = m.group(1), m.group(2)
                if sk not in entries:
                    bad.append(f"{p}: {m.group(0)} — no such skill")
                elif vb and vb not in entries[sk]:
                    bad.append(f"{p}: {m.group(0)} — {sk} has no verb '{vb}'")
    return bad


# ── Obligation 3: render by kind · Obligation 5: resolve tokens ─────────────────


def org_prefix(target):
    """§1.6 branding token. Resolves to "<Org> " or, with no org configured, to nothing.

    Six guidelines open with `# Python Standards — __ORG_PREFIX__shared standard`. The
    scaffold has always resolved this when it copies a guideline into a generated repo's
    docs/; this adapter did not, so every installed guideline carried the literal token in
    its H1. Same file, two consumers, one of which knew about the token.

    `scaffold-profile.md` is now the whole profile — the applied JSON this used to read
    is gone, because two files holding the same 22 keys is one file too many. So the
    value is parsed out of the sheet, and the parse must survive what a sheet contains
    that a JSON object could not: `org:` lines carrying an example hint
    (`org:          # e.g. Acme`), and prose. Hence — matching profile.py's `parse`, which
    owns this format — a trailing " # …" is stripped, a value that is only a hint counts
    as blank, and the key must sit at the start of the line.

    A naive regex here returns the hint as the org name and brands every installed
    guideline "# Python Standards — # e.g. Acme shared standard". That is the failure this
    docstring used to describe as a reason not to read the sheet at all.

    Only the install-wide profile: guidelines are installed once per machine, so a
    project-scoped profile cannot reach them (see STANDARD.md §1.6).
    """
    p = os.path.join(target, "scaffold-profile.md")
    v = ""
    try:
        with open(p, encoding="utf-8") as f:
            for raw in f:
                m = re.match(r"^org\s*:\s*(.*)$", raw.strip())
                if not m:
                    continue
                val = re.sub(r"\s+#.*$", "", m.group(1)).strip()
                if val and not val.startswith("#"):
                    v = val
                break
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        # A missing or unreadable profile must not break the install; the token resolves
        # to nothing, which is exactly what an unbranded install should look like.
        return ""
    return f"{v} " if v and not v.startswith("TODO_SET") else ""


# §1.6 / obligation 12: the directory name that marks a project scope for per-project
# user state. Claude's per-project configuration lives in a `.claude/` beside the code,
# so a project profile belongs there too — core/ must not know that, which is the whole
# reason this is a token and not a string in a skill.
PROJECT_SCOPE_DIR = ".claude"


def substitute(text, skill_dir, data_dir, guide_dir, org=""):
    text = text.replace("__SKILL_DIR__", skill_dir)
    text = text.replace("__KIT_DATA_DIR__", data_dir)
    text = text.replace("__GUIDELINES_DIR__", guide_dir)
    text = text.replace("__PROJECT_SCOPE_DIR__", PROJECT_SCOPE_DIR)
    text = text.replace("__ORG_PREFIX__", org)
    text = re.sub(r"\{\{cmd:([a-z-]+):([a-z-]+)\}\}", r"/\1:\2", text)
    text = re.sub(r"\{\{cmd:([a-z-]+)\}\}", r"/\1", text)
    text = text.replace("{{args}}", "$ARGUMENTS")
    return text


def scalar(v):
    """A YAML plain scalar, quoted only when leaving it bare would change its type.

    `arguments` is prose written for a human — "[path to a .drawio file; default = …]".
    Emitted bare, YAML reads the leading `[` as a flow sequence and the value arrives as a
    *list*, and a consumer that type-checks its frontmatter can reject the whole block —
    taking `description` down with it. Prose is not required to dodge another format's
    metacharacters; the adapter that chose the format quotes it.
    """
    v = " ".join(str(v).split())
    risky = v[:1] in "[]{}>|&*!%@`\"'#," or ": " in v or " #" in v or v[:2] == "- "
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"' if risky else v


def render_fm(fm, kind):
    """Claude's frontmatter. applies_to is folded into the description (D-08) — the trigger
    belongs where the model reads it, and a hook firing on every edit becomes noise.

    A command gets no `name`: Claude derives the command name from the file's path, so
    writing `name: build` next to a command invoked as `/diagram:build` states a second,
    wrong name. It gets `description` — which is the line the slash-command picker shows —
    and `argument-hint`.
    """
    desc = " ".join(fm.get("description", "").split())
    globs = fm.get("applies_to__list")
    if globs:
        desc += " Applies to " + ", ".join(f"`{g}`" for g in globs) + "."
    out = "---\n"
    if kind != "command":
        out += f"name: {scalar(fm['name'])}\n"
    out += f"description: {scalar(desc)}\n"
    if kind in ("skill", "command") and fm.get("arguments"):
        out += f"argument-hint: {scalar(fm['arguments'])}\n"
    return out + "---\n\n"


# Copied with the skill, or deliberately left behind. §1.4: an adapter installs payload but
# not documentation — "docs" is a directory name here, so a skill's whole docs/ tree
# (workflow diagrams and the like) stays in the repo rather than shipping a PNG into every
# install. Contrast reference/, which the skill itself reads at run time and so must ship.
PAYLOAD_SKIP = {
    "__pycache__",
    ".ruff_cache",
    ".DS_Store",
    "README.md",
    "docs",
    "commands",
    "SKILL.md",
}


def install(target, dry_run):
    arts = discover()
    errs, entries = validate(arts)
    if errs:
        for e in errs:
            print(f"         {RED}✗{R}  {e}")
        die("validation failed — nothing was written")
    ok(f"{len(arts)} artifacts, frontmatter valid")

    bad = check_refs(entries)
    if bad:
        for b in bad[:10]:
            print(f"         {RED}✗{R}  {b}")
        die("unresolvable command reference — nothing was written")
    ok("every {{cmd:…}} resolves")

    data_dir = target
    guide_dir = os.path.join(target, "guidelines")
    written = {
        "guidelines": [],
        "conformance": [],
        "skills": [],
        "commands": [],
        "agents": [],
    }

    def write(path, text):
        if dry_run:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    # Obligation 6: replace, do not merge — but never the kit data dir (obligation 11).
    for sub in ("guidelines", "skills", "commands", "agents"):
        d = os.path.join(target, sub)
        if dry_run:
            continue
        # A previous setup may have symlinked one of these elsewhere; rmtree refuses a
        # symlink, and following it would delete the target's contents instead.
        if os.path.islink(d):
            os.unlink(d)
        elif os.path.isdir(d):
            shutil.rmtree(d)

    org = org_prefix(target)

    for kind, name, path in arts:
        fm, body = parse(path)
        skill_dir = os.path.join(target, "skills", name)
        sub = lambda t: substitute(t, skill_dir, data_dir, guide_dir, org)

        if kind == "guideline":
            write(
                os.path.join(guide_dir, f"{name}.md"),
                sub(open(path, encoding="utf-8").read()),
            )
            written["guidelines"].append(name)
            # Obligation 4: the checklist sibling travels with the guideline as payload —
            # copied beside it so a reviewer can read it by path, never registered (§1.2).
            csrc = conformance_src(name)
            if csrc:
                write(
                    os.path.join(guide_dir, f"{name}{CONFORMANCE_SUFFIX}"),
                    sub(open(csrc, encoding="utf-8").read()),
                )
                written["conformance"].append(name)
            # The registration copy carries the rules only. Folding the checklist in here
            # would put it back on the implementer's hot path, which is the whole point.
            write(
                os.path.join(skill_dir, "SKILL.md"),
                render_fm(fm, kind) + sub(body).lstrip("\n"),
            )
            written["skills"].append(name)

        elif kind == "subagent":
            write(
                os.path.join(target, "agents", f"{name}.md"),
                render_fm(fm, kind) + sub(body).lstrip("\n"),
            )
            written["agents"].append(name)

        else:  # skill
            write(
                os.path.join(skill_dir, "SKILL.md"),
                render_fm(fm, kind) + sub(body).lstrip("\n"),
            )
            written["skills"].append(name)
            src = os.path.dirname(path)
            # Obligation 4: payload travels with the skill but is never registered. Only
            # SKILL.md and commands/*.md at depth 1 become entry points (§1.4).
            for r, dirs, fs in os.walk(src):
                dirs[:] = [d for d in dirs if d not in PAYLOAD_SKIP]
                for f in fs:
                    if f in PAYLOAD_SKIP:
                        continue
                    s = os.path.join(r, f)
                    dst = os.path.join(skill_dir, os.path.relpath(s, src))
                    if dry_run:
                        continue
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    try:
                        write(dst, sub(open(s, encoding="utf-8").read()))
                    except UnicodeDecodeError:
                        shutil.copy2(s, dst)
            cdir = os.path.join(src, "commands")
            for verb in sorted(entries.get(name, [])):
                cfm, cbody = parse(os.path.join(cdir, f"{verb}.md"))
                write(
                    os.path.join(target, "commands", name, f"{verb}.md"),
                    render_fm(cfm, "command") + sub(cbody).lstrip("\n"),
                )
                written["commands"].append(f"{name}:{verb}")

    return written, arts


# ── Obligation 8: verify ────────────────────────────────────────────────────────


def verify(target, written, arts, profile_before, dry_run):
    fails = []
    declared = sum(1 for k, _, _ in arts if k in ("guideline", "skill")) + len(
        written["commands"]
    )
    if not dry_run:
        got = len([1 for n in os.listdir(os.path.join(target, "skills"))]) + len(
            [
                1
                for n, _, fs in os.walk(os.path.join(target, "commands"))
                for f in fs
                if f.endswith(".md")
            ]
        )
        if got != declared:
            fails.append(f"registered {got} entry points, declared {declared}")
        # §2.4: every sibling installed, and none of them registered anywhere.
        for n in written["conformance"]:
            if not os.path.isfile(
                os.path.join(target, "guidelines", f"{n}{CONFORMANCE_SUFFIX}")
            ):
                fails.append(f"conformance sibling not installed: {n}")
            if os.path.exists(os.path.join(target, "skills", f"{n}.conformance")):
                fails.append(f"conformance sibling registered as a skill: {n}")
        # Scan ONLY what this installer wrote. The target is also the kit data dir, full of
        # the user's transcripts and history — the first version walked all of it and
        # "found" unresolved markers inside a session log of someone discussing the markers.
        left = {}
        for sub in ("guidelines", "skills", "commands", "agents"):
            for r, _, fs in os.walk(os.path.join(target, sub)):
                for f in fs:
                    p = os.path.join(r, f)
                    try:
                        t = open(p, encoding="utf-8").read()
                    except Exception:
                        continue
                    # A general scan, not a list of the markers we happen to know about.
                    # This was three hardcoded names, and a denylist fails open exactly the
                    # way §1.4 describes: __ORG_PREFIX__ was never on the list, so six
                    # guidelines shipped with the literal token in their H1 heading and
                    # every install reported "no unresolved markers". MARKER_RE catches the
                    # next one too, whatever it turns out to be called.
                    for m in set(MARKER_RE.findall(t)):
                        left.setdefault(m, []).append(p)
        if left:
            for m, ps in sorted(left.items()):
                fails.append(
                    f"unresolved marker {m} in {len(ps)} file(s), e.g. {ps[0]}"
                )
        after = _profile_hash(target)
        if profile_before != after:
            fails.append("the profile sheet changed during install (obligation 7)")
    return fails, declared


def _profile_hash(target):
    out = []
    for n in ("scaffold-profile.md", "scaffold-profile.json"):
        p = os.path.join(target, n)
        out.append(open(p, "rb").read() if os.path.exists(p) else b"")
    return out


# ── Obligation 10: uninstall ────────────────────────────────────────────────────

RECEIPT = ".agent-kit-install.json"


def uninstall(target, dry_run):
    """Remove exactly what the receipt lists, and nothing else.

    Driven by the receipt rather than by a re-scan of core/, so an artifact deleted from
    core/ since the install is still removed, and a file the user put in the target by hand
    is still left alone. The target itself is the kit data dir and is never removed.
    """
    rp = os.path.join(target, RECEIPT)
    if not os.path.exists(rp):
        die(f"no receipt at {rp} — nothing to uninstall")
    r = json.load(open(rp))

    paths = [os.path.join(target, "guidelines", f"{n}.md") for n in r["guidelines"]]
    # Receipts written before conformance siblings existed have no such key.
    paths += [
        os.path.join(target, "guidelines", f"{n}{CONFORMANCE_SUFFIX}")
        for n in r.get("conformance", [])
    ]
    paths += [os.path.join(target, "skills", n) for n in r["skills"]]
    paths += [os.path.join(target, "agents", f"{n}.md") for n in r["agents"]]
    paths += [
        os.path.join(
            target, "commands", *c.split(":", 1)[:1], c.split(":", 1)[1] + ".md"
        )
        for c in r["commands"]
    ]

    gone = 0
    for p in paths:
        if not os.path.lexists(p):
            continue
        gone += 1
        if dry_run:
            continue
        shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)

    if not dry_run:
        # Directories the install created are removed only once empty — anything the user
        # added alongside the kit survives.
        for sub in ("guidelines", "skills", "commands", "agents"):
            d = os.path.join(target, sub)
            for r_, dirs, _ in os.walk(d, topdown=False):
                if os.path.isdir(r_) and not os.listdir(r_):
                    os.rmdir(r_)
        os.remove(rp)

    ok(f"{gone} artifact(s) removed" + (" (dry run)" if dry_run else ""))
    note(f"kit data dir kept: {target}")
    return gone


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("target", nargs="?", default=os.path.expanduser("~/.claude"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--uninstall",
        action="store_true",
        help="remove exactly what the receipt lists; never the kit data dir",
    )
    ap.add_argument(
        "--no-profile",
        action="store_true",
        help="accepted for compatibility; the "
        "profile is never regenerated by this installer",
    )
    a = ap.parse_args()
    target = os.path.abspath(os.path.expanduser(a.target))
    if os.path.basename(target) != ".claude":
        target = os.path.join(target, ".claude")

    total = 4
    print(f"\n  {B}agent-kit → Claude{R}\n  {DIM}{LINE}{R}")
    print(f"  {'source':10} {ROOT}")
    print(
        f"  {'target':10} {B}{target}{R}"
        + (f"  {YLW}(dry run){R}" if a.dry_run else "")
    )

    if a.uninstall:
        step("Uninstalling", 1)
        uninstall(target, a.dry_run)
        print(f"\n  {DIM}{LINE}{R}\n  {GRN}✓  Uninstalled{R}\n")
        return

    step("Checking prerequisites", total)
    if not os.path.isdir(CORE):
        die(f"no core/ at {CORE}")
    os.makedirs(target, exist_ok=True)
    if not os.access(target, os.W_OK):
        die(f"{target} is not writable")
    ok(f"python {sys.version.split()[0]} · target writable")
    profile_before = _profile_hash(target)

    step("Validating core/ (nothing is written until this passes)", total)
    written, arts = install(target, a.dry_run)

    step("Rendering", total)
    for k, label in (
        ("guidelines", "guideline"),
        ("skills", "skill artifact"),
        ("commands", "command"),
        ("agents", "subagent"),
    ):
        ok(f"{len(written[k]):2} {label}(s)")
    note(
        "guidelines render twice: canonical for __GUIDELINES_DIR__, plus a model-invocable copy"
    )

    step("Verifying", total)
    fails, declared = verify(target, written, arts, profile_before, a.dry_run)
    if a.dry_run:
        warn("dry run — nothing written, verification skipped")
    elif fails:
        for f in fails:
            print(f"         {RED}✗{R}  {f}")
        die("install verification failed")
    else:
        ok(f"{declared} entry points registered, zero payload")
        ok("no unresolved markers")
        ok("profile sheet untouched")

    if not a.dry_run:
        # Obligation 9: the receipt is what --uninstall is driven by, so it must list every
        # artifact by name — a summary count would leave nothing to remove precisely.
        receipt = {
            "source": ROOT,
            "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "adapter": "claude",
            **written,
        }
        with open(os.path.join(target, ".agent-kit-install.json"), "w") as f:
            json.dump(receipt, f, indent=2)
        note("receipt: .agent-kit-install.json")

    print(f"\n  {DIM}{LINE}{R}")
    print(
        f"  {GRN}✓  Installed{R}  {DIM}{len(written['guidelines'])} guidelines "
        f"({len(written['conformance'])} with a conformance sheet) · "
        f"{len(written['skills']) - len(written['guidelines'])} skills · "
        f"{len(written['commands'])} commands · {len(written['agents'])} subagents{R}"
    )
    print(f"  {DIM}{LINE}{R}\n")
    for c in written["commands"]:
        print(f"    {CYA}/{c}{R}")
    print()


if __name__ == "__main__":
    main()
