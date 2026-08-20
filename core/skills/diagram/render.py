#!/usr/bin/env python3
"""Export a .drawio file to PNG so it can be looked at before it is delivered.

    python3 render.py <file.drawio> [--output <file.png>] [--scale 1.5] [--page 1]
    python3 render.py --which          # print the draw.io binary that would be used

The draw.io binary is resolved at run time — nothing is hardcoded to one machine:

    --bin  >  $DRAWIO_BIN  >  profile `drawio_bin`  >  PATH (`drawio`)  >  the usual
    install locations for this OS

Exit codes: 0 rendered · 2 no usable draw.io binary · 3 export failed.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _kit_data_dir():
    """The kit's shared data directory: one per install, shared by every skill, and never
    replaced by an install (unlike the skill dir, which is). __KIT_DATA_DIR__ is rewritten
    at install time; the fallbacks keep this working from a repo checkout."""
    d = os.environ.get("AGENT_KIT_DATA_DIR") or "__KIT_DATA_DIR__"
    if not d.startswith("__"):
        return d
    p = _HERE
    while p != os.path.dirname(p):
        if os.path.exists(os.path.join(p, "STANDARD.md")):
            return p
        p = os.path.dirname(p)
    return os.path.dirname(os.path.dirname(_HERE))


# Where each OS puts a desktop draw.io install. Checked only after the explicit
# sources (flag, env, profile, PATH) come up empty.
_KNOWN_LOCATIONS = {
    "darwin": [
        "/Applications/draw.io.app/Contents/MacOS/draw.io",
        os.path.expanduser("~/Applications/draw.io.app/Contents/MacOS/draw.io"),
    ],
    "linux": [
        "/usr/bin/drawio",
        "/usr/local/bin/drawio",
        "/opt/drawio/drawio",
        "/snap/bin/drawio",
    ],
    "win32": [
        r"C:\Program Files\draw.io\draw.io.exe",
        r"C:\Program Files (x86)\draw.io\draw.io.exe",
    ],
}


def _project_scope_dir():
    """The directory name that marks a project scope — the tool's per-project config
    folder, resolved at install time because core/ must not know what any one tool calls
    its directories (§1.6).

    Empty when the token is unresolved, i.e. running from an uninstalled checkout: with
    no adapter there is no project convention to honour. $AGENT_KIT_PROJECT_DIR is the
    escape hatch, and how a repo checkout exercises project scoping without installing.
    """
    d = os.environ.get("AGENT_KIT_PROJECT_DIR") or "__PROJECT_SCOPE_DIR__"
    return "" if d.startswith("__") else d


# The profile format, duplicated from the scaffold skill's profile.py, which owns it —
# same reason ``_kit_data_dir`` is duplicated: this skill must work when that one is not
# installed. `key: value` lines; a trailing " # hint" is a comment, a value that is only
# a hint counts as blank, and the key charset excludes "/" and "." so a value's own colon
# (https://…) cannot be read as a key.
_LINE_RE = re.compile(r"^-?\s*([a-z][a-z0-9_]*)\s*:\s*(.*)$")
_COMMENT_RE = re.compile(r"\s+#.*$")


def _parse_profile(path):
    values = {}
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                m = _LINE_RE.match(raw.strip())
                if not m:
                    continue
                val = _COMMENT_RE.sub("", m.group(2)).strip()
                if val and not val.startswith("#"):
                    values[m.group(1)] = val
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        return {}
    return values


def _profile_path(start=None):
    """Which profile this run uses, where it came from, and what it may be shadowing.

    One machine serves more than one client, and the profile holds exactly the values
    that differ between them — for this skill, the brand guide a diagram is drawn to.
    A single install-wide profile is therefore how one client's palette ends up on
    another client's diagram. So the profile is SCOPED: the nearest project profile
    above the working directory wins over the install-wide one.

        $AGENT_KIT_PROFILE                     an explicit file, for one invocation
        <dir>/<scope dir>/scaffold-profile.md  nearest project profile, walking up
        <kit data dir>/scaffold-profile.md     install-wide fallback

    Returns ``(path, scope, shadowed)``. ``scope`` is "env" | "project" | "global".
    ``shadowed`` is the nearest project scope directory with NO profile of its own, or
    None. Kept in step with the copy in the scaffold skill's profile.py, which owns the
    rule; duplicated rather than imported so this skill works without that one, exactly
    as ``_kit_data_dir`` above is.
    """
    env = os.environ.get("AGENT_KIT_PROFILE")
    if env:
        return os.path.expanduser(os.path.expandvars(env)), "env", None
    root = os.path.abspath(_kit_data_dir())
    scope_name = _project_scope_dir()
    here, shadowed = os.path.abspath(start or os.getcwd()), None
    while scope_name:
        d = os.path.join(here, scope_name)
        if os.path.abspath(d) != root and os.path.isdir(d):
            cand = os.path.join(d, "scaffold-profile.md")
            if os.path.isfile(cand):
                return cand, "project", None
            shadowed = shadowed or d
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return os.path.join(root, "scaffold-profile.md"), "global", shadowed


def _load_profile():
    """The profile governing the working directory (see ``_profile_path``)."""
    path, _scope, _shadowed = _profile_path()
    return _parse_profile(path)


def resolve_binary(cli_value=""):
    """First usable draw.io binary, or None. Order: flag > env > profile > PATH > known."""
    candidates = [
        cli_value,
        os.environ.get("DRAWIO_BIN", ""),
        _load_profile().get("drawio_bin", ""),
    ]
    for cand in candidates:
        if not cand:
            continue
        path = os.path.expanduser(os.path.expandvars(cand))
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    for name in ("drawio", "draw.io"):
        found = shutil.which(name)
        if found:
            return found
    for path in _KNOWN_LOCATIONS.get(sys.platform, []):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def render(src, out=None, scale=1.5, page=0, binary=None, transparent=False):
    """Export `src` to PNG. Returns the output path; raises RuntimeError on failure."""
    src = os.path.abspath(os.path.expanduser(src))
    out = (
        os.path.abspath(os.path.expanduser(out))
        if out
        else os.path.splitext(src)[0] + ".png"
    )
    cmd = [
        binary,
        "--export",
        "--format",
        "png",
        "--scale",
        str(scale),
        "--page-index",
        str(page),
        "--output",
        out,
        src,
    ]
    if transparent:
        cmd.insert(-2, "--transparent")
    # draw.io desktop is an Electron app; it needs a writable HOME and, on a headless
    # box, a display. Keep the environment intact and let it report its own errors.
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(out):
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            detail or f"draw.io exited {proc.returncode} without writing {out}"
        )
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="Export a .drawio file to PNG.")
    p.add_argument("file", nargs="?", help="the .drawio file to export")
    p.add_argument(
        "--output", default="", help="PNG path (default: alongside the source)"
    )
    p.add_argument("--scale", default="1.5", help="export scale (default: 1.5)")
    # 1-based: draw.io numbered --page-index from 0 before v27.0.2 and from 1
    # after it. Defaulting to 0 made every render of a single-page file fail with
    # "Invalid page index" against a current binary.
    p.add_argument("--page", default="1", help="page number, 1-based (default: 1)")
    p.add_argument(
        "--bin", default="", help="draw.io binary (overrides env/profile/PATH)"
    )
    p.add_argument("--transparent", action="store_true", help="transparent background")
    p.add_argument(
        "--which", action="store_true", help="print the resolved binary, then exit"
    )
    p.add_argument(
        "--profile",
        action="store_true",
        help="print the profile governing this directory (brand guide, output "
        "folder) and its scope, then exit",
    )
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    # The brand guide and output folder come from a profile, and which profile that is
    # depends on where you are standing. Printed on request so the answer is read, not
    # assumed — a diagram drawn to another client's palette looks entirely fine.
    if args.profile:
        path, scope, shadowed = _profile_path()
        print(f"profile: {scope:<7} {path}")
        if shadowed:
            print(f"         ! {shadowed} has no profile of its own — this")
            print("           directory falls back to the machine-wide profile")
        prof = _load_profile()
        print(json.dumps(prof, indent=2, sort_keys=True) if prof else "(no profile)")
        return 0

    binary = resolve_binary(args.bin)
    if args.which:
        print(binary or "(no draw.io binary found)")
        return 0 if binary else 2
    if not args.file:
        p.error("a .drawio file is required (or pass --which)")
    if not binary:
        print(
            "ERROR: no draw.io binary found.\n"
            "       Install draw.io desktop, then point at it with one of:\n"
            "         --bin /path/to/draw.io\n"
            "         DRAWIO_BIN=/path/to/draw.io\n"
            "         drawio_bin in the shared profile sheet (apply with {{cmd:scaffold:profile}})",
            file=sys.stderr,
        )
        return 2

    try:
        out = render(
            args.file, args.output, args.scale, args.page, binary, args.transparent
        )
    except RuntimeError as exc:
        print(f"ERROR: export failed — {exc}", file=sys.stderr)
        return 3
    print(f"Rendered {out}")
    print("  Now LOOK at it — read the PNG and run the checklist before delivering.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
