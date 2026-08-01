#!/usr/bin/env python3
"""Fill a repo's ``TODO_SET_*`` placeholders from a one-page CONFIG.md.

Two modes:

  --generate            (Re)write ``<repo>/CONFIG.md`` listing the ``TODO_SET_*``
                        tokens the repo still contains, grouped and annotated. Only
                        unresolved tokens appear, so the sheet always matches reality.

  (default) apply       Parse ``<repo>/CONFIG.md`` and replace every filled token
                        across the whole repo tree. ``--dry-run`` previews without
                        writing. The sheet itself is never rewritten, so the keys
                        survive and the step is safe to re-run.

Values are applied by exact token match (``TODO_SET_X`` -> value), so the keys in
CONFIG.md must not be renamed. Blank lines are left as placeholders.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_tokens import META, TOKENS  # noqa: E402

CONFIG_NAME = "CONFIG.md"
SKIP_DIRS = {
    ".git",
    ".databricks",
    "bundle",
    "wheels",
    ".venv",
    "venv",
    "__pycache__",
    ".ruff_cache",
    ".idea",
    ".vscode",
}
TOKEN_RE = re.compile(r"TODO_SET_[A-Z0-9_]+")
# Accepts "TOKEN: value" with an optional leading "- " and an optional trailing
# "# hint" comment (the generated hint, or one the user left in place).
LINE_RE = re.compile(r"^-?\s*(TODO_SET_[A-Z0-9_]+)\s*:\s*(.*)$")
TRAILING_COMMENT_RE = re.compile(r"\s+#.*$")


def _iter_files(repo_dir):
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            yield os.path.join(root, fn)


def scan_tokens(repo_dir, skip_config=True):
    """Return ``{token: [repo-relative files]}`` for every TODO_SET_* in the tree."""
    found = {}
    for path in _iter_files(repo_dir):
        if skip_config and os.path.basename(path) == CONFIG_NAME:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, IsADirectoryError):
            continue
        for tok in set(TOKEN_RE.findall(text)):
            found.setdefault(tok, []).append(os.path.relpath(path, repo_dir))
    return {k: sorted(v) for k, v in found.items()}


def _group_of(tok):
    return META[tok][1] if tok in META else "Other"


def generate(repo_dir, display_name, preserve=True):
    """Write ``<repo>/CONFIG.md``. Returns ``(path, present_tokens_dict)``.

    ``preserve`` keeps any value already typed into an existing sheet, so
    regenerating after ``{{cmd:scaffold:add}}`` introduces new placeholders never
    discards work in progress. A token that no longer appears anywhere in the
    tree is dropped either way — its value has already been applied.
    """
    present = scan_tokens(repo_dir)
    existing = {}
    if preserve:
        path = os.path.join(repo_dir, CONFIG_NAME)
        if os.path.exists(path):
            existing = parse(path)
    known = [tok for (tok, *_) in TOKENS if tok in present]
    unknown = sorted(t for t in present if t not in META)
    ordered = known + unknown

    lines = [
        f"# {display_name} — Configuration",
        "",
        "Fill in the values after each colon (leave blank to skip), then apply with",
        "`{{cmd:scaffold:configure}}`. Keep the keys as-is.",
        "",
    ]

    if not ordered:
        lines += ["Nothing to fill — no placeholders remain.", ""]
    else:
        emitted = []
        for tok in ordered:
            g = _group_of(tok)
            if g not in emitted:
                emitted.append(g)
        # pad keys so inline hints line up
        width = max(len(tok) for tok in ordered) + 2
        for g in emitted:
            lines.append(f"## {g}")
            for tok in ordered:
                if _group_of(tok) != g:
                    continue
                if tok in META:
                    _, _, label, example = META[tok]
                    hint = f"e.g. {example}" if example else label
                else:
                    hint = ""
                key = f"{tok}:"
                val = existing.get(tok, "")
                if val:  # already typed in — carry it over, hint no longer needed
                    lines.append(f"{key.ljust(width)}{val}")
                else:
                    lines.append(f"{key.ljust(width)}# {hint}" if hint else key)
            lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    path = os.path.join(repo_dir, CONFIG_NAME)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path, present


def parse(config_path):
    """Return ``{token: value}`` for every filled (non-blank) line in the sheet."""
    values = {}
    with open(config_path, encoding="utf-8") as f:
        for raw in f:
            m = LINE_RE.match(raw.strip())
            if not m:
                continue
            tok = m.group(1)
            val = TRAILING_COMMENT_RE.sub("", m.group(2)).strip()
            if val and not val.startswith("#"):  # skip blanks and hint-only lines
                values[tok] = val
    return values


def apply(repo_dir, values, dry_run=False):
    """Replace filled tokens across the tree (skipping CONFIG.md).

    Returns ``{token: files_changed_count}``.
    """
    counts = {t: 0 for t in values}
    for path in _iter_files(repo_dir):
        if os.path.basename(path) == CONFIG_NAME:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, IsADirectoryError):
            continue
        new = text
        for tok, val in values.items():
            if tok in new:
                new = new.replace(tok, val)
                counts[tok] += 1
        if new != text and not dry_run:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Fill a repo's TODO_SET_* placeholders from CONFIG.md."
    )
    ap.add_argument("--repo", required=True, help="path to the repo")
    ap.add_argument(
        "--generate",
        action="store_true",
        help="(re)write CONFIG.md from the repo's remaining placeholders, then exit",
    )
    ap.add_argument(
        "--display-name",
        default=None,
        help="title for the generated sheet (default: repo folder name)",
    )
    ap.add_argument("--file", default=None, help="config sheet path (default: <repo>/CONFIG.md)")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="preview the apply without writing any files",
    )
    args = ap.parse_args(argv)

    repo = os.path.abspath(args.repo)
    if not os.path.isdir(repo):
        ap.error(f"repo not found: {repo}")
    config_path = args.file or os.path.join(repo, CONFIG_NAME)

    if args.generate:
        name = args.display_name or os.path.basename(repo.rstrip("/"))
        path, present = generate(repo, name)
        print(f"Wrote {path}")
        if present:
            print(f"  {len(present)} placeholder(s) to fill: {', '.join(sorted(present))}")
        else:
            print("  no TODO_SET_ placeholders remain in this repo")
        return 0

    if not os.path.exists(config_path):
        ap.error(f"config sheet not found: {config_path}\n  run with --generate first")

    values = parse(config_path)
    if not values:
        remaining = scan_tokens(repo)
        print("No filled values found in the sheet (every line is blank). Nothing applied.")
        if remaining:
            print(
                f"  {len(remaining)} placeholder(s) still unresolved: {', '.join(sorted(remaining))}"
            )
        return 0

    counts = apply(repo, values, dry_run=args.dry_run)
    verb = "Would set" if args.dry_run else "Set"
    print(f"{verb} {len(values)} value(s):")
    for tok, val in values.items():
        shown = val if len(val) <= 48 else val[:45] + "..."
        print(f"  {tok:<32} -> {shown}   ({counts[tok]} file(s))")

    remaining = scan_tokens(repo)
    if args.dry_run:
        still = sorted(t for t in remaining if t not in values)
    else:
        still = sorted(remaining)
    print()
    if still:
        print(f"  Still unresolved ({len(still)}): {', '.join(still)}")
    else:
        print("  All TODO_SET_ placeholders resolved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
