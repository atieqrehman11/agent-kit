#!/usr/bin/env python3
"""Export a .drawio file to PNG so it can be looked at before it is delivered.

    python3 render.py <file.drawio> [--output <file.png>] [--scale 1.5] [--page 0]
    python3 render.py --which          # print the draw.io binary that would be used

The draw.io binary is resolved at run time — nothing is hardcoded to one machine:

    --bin  >  $DRAWIO_BIN  >  profile `drawio_bin`  >  PATH (`drawio`)  >  the usual
    install locations for this OS

Exit codes: 0 rendered · 2 no usable draw.io binary · 3 export failed.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

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


def _load_profile():
    """Shared install profile saved by /scaffold:profile, in the .claude/ root."""
    root = os.path.dirname(os.path.dirname(_HERE))
    try:
        with open(os.path.join(root, "scaffold-profile.json"), encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, str) and v.strip()}
    except (FileNotFoundError, ValueError):
        return {}


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
    p.add_argument("--page", default="0", help="page index (default: 0)")
    p.add_argument(
        "--bin", default="", help="draw.io binary (overrides env/profile/PATH)"
    )
    p.add_argument("--transparent", action="store_true", help="transparent background")
    p.add_argument(
        "--which", action="store_true", help="print the resolved binary, then exit"
    )
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

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
            "         drawio_bin in the shared profile sheet (apply with /scaffold:profile)",
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
