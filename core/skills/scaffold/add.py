#!/usr/bin/env python3
"""Add one aspect of the scaffold to a repo that **already exists**.

``new.py`` creates a whole repo. This adds a single slice to a repo you already
have, including repos this tool never created. Two aspects are choosable:

    deploy the deploy config — databricks.yml + resources/ + run_local.sh
    gitlab the GitLab pipeline — .gitlab-ci.yml +
           run_resources.yml + .bundleignore, and on a job repo the
           config/{DEV,STG,PROD} it reads per target
    api    the use case API surface — GET /v1/health + GET /v1/info

Usage:
    python3 add.py --repo <path> --detect
    python3 add.py --repo <path> --aspect deploy [--aspect gitlab] [--aspect api]
    python3 add.py --repo <path> --aspect all --dry-run
    python3 add.py --list

A ``.gitignore`` and a regenerated ``CONFIG.md`` come with any add, wherever they
are missing — those are hygiene, not decisions, so they are never asked about.

Safety rules, because the target is someone's working repo:
  * Only the files the chosen aspect owns are written. Nothing else in the repo is
    rewritten — in particular no tree-wide token substitution, unlike ``new.py``.
  * An existing file is **skipped and reported**, never silently replaced. With
    ``--force`` the previous content is kept beside it as ``<name>.bak``.
  * ``--dry-run`` prints the exact plan and writes nothing.

Values come from the repo itself first (type, bundle name/uuid, slug), then the
shared install profile, then a ``TODO_SET_*`` placeholder that ``CONFIG.md`` +
``{{cmd:scaffold:configure}}`` resolve in one pass — the same order ``new.py`` uses.
"""

import argparse
import os
import re
import sys
import uuid as _uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aspects  # noqa: E402
import configure  # noqa: E402

# Reused rather than re-declared: the profile loader and the profile-key ->
# TODO_SET_ token map must behave identically in `new` and `add`, or the same
# profile would produce two different repos.
from new import _PROFILE_TODO_TOKENS, _load_profile, profilelib  # noqa: E402

_TYPE_SUFFIX_RE = re.compile(r"-(?:" + "|".join(aspects.ALL_TYPES) + r")$")


def parse_args(argv):
    p = argparse.ArgumentParser(
        description="Add one aspect of the scaffold to an existing repo."
    )
    p.add_argument("--repo", default=None, help="path to the existing repo")
    p.add_argument(
        "--aspect",
        action="append",
        default=[],
        metavar="KEY",
        # Validated in _resolve_keys, not by argparse: a retired key deserves a
        # "that lives in X now" message rather than an invalid-choice list.
        help="aspect to add: "
        + " | ".join(aspects.SELECTABLE)
        + " (repeatable); 'all' = the standard set for this repo type, minus what "
        "is already there",
    )
    p.add_argument(
        "--detect",
        action="store_true",
        help="report the repo's type and each aspect's status, then exit",
    )
    p.add_argument(
        "--list", action="store_true", help="list the available aspects, then exit"
    )
    p.add_argument(
        "--type",
        default=None,
        choices=aspects.ALL_TYPES,
        help="repo type (default: detected from the repo)",
    )
    p.add_argument("--slug", default=None, help="kebab slug (default: from repo name)")
    p.add_argument(
        "--display-name", default=None, help="default: Title Case of the slug"
    )
    p.add_argument("--description", default=None, help="one sentence (api aspect)")
    p.add_argument("--catalog", default=None, help="Unity Catalog (skippable)")
    p.add_argument("--table-prefix", default=None, help="table name prefix (skippable)")
    p.add_argument("--team-name", default=None, help="team name (skippable)")
    p.add_argument("--team-email", default=None, help="team email (skippable)")
    p.add_argument(
        "--gitlab-runner", default=None, help="GitLab runner tag (skippable)"
    )
    p.add_argument(
        "--controller-project-id",
        default=None,
        help="CI/CD controller project id (skippable)",
    )
    p.add_argument("--data-sensitivity", default="pii")
    p.add_argument(
        "--no-config-sheet",
        action="store_true",
        help="do not (re)generate CONFIG.md after adding",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing files (each is backed up as <name>.bak first)",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="print the plan; write nothing"
    )
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.list:
        _print_list()
        return 0

    if not args.repo:
        print("ERROR: --repo is required (or use --list).", file=sys.stderr)
        return 2

    repo = os.path.abspath(os.path.expanduser(os.path.expandvars(args.repo)))
    if not os.path.isdir(repo):
        print(f"ERROR: repo not found: {repo}", file=sys.stderr)
        return 2

    detected, reason = aspects.detect_type(repo)
    rtype = args.type or detected
    if not rtype:
        print(
            f"ERROR: could not tell what kind of repo {os.path.basename(repo)} is "
            f"({reason}).\n       Pass --type {{{'|'.join(aspects.ALL_TYPES)}}}.",
            file=sys.stderr,
        )
        return 2
    type_note = (
        f"{rtype}  (given)" if args.type else f"{rtype}  (detected from {reason})"
    )

    bundle_name, bundle_uuid = aspects.read_bundle(repo)

    if args.detect:
        _print_detect(repo, rtype, type_note, bundle_name, bundle_uuid)
        return 0

    keys = _resolve_keys(args.aspect, repo, rtype)
    if keys is None:  # bad input
        return 2
    if not keys:  # `--aspect all` on a repo that already has everything
        return 0

    ctx, notes = _build_vars(args, repo, rtype, bundle_name, bundle_uuid, keys)

    print("=" * 66)
    print(f"  Repo:    {repo}")
    print(f"  Type:    {type_note}")
    print(f"  Adding:  {', '.join(keys)}" + ("   [dry run]" if args.dry_run else ""))
    # `add` writes the org's CI controller, groups and policies into an existing repo,
    # so say which profile they came from — up here, before the files, for the same
    # reason `new` does it: a wrongly-branded repo is cheap to prevent and expensive
    # to notice later. Not a "heads-up" note at the end; those come after the writing.
    _p, _s, _sh = profilelib._profile_path()
    for line in profilelib.report(_p, _s, _sh, profilelib.load(_p), prefix="  "):
        print(line)
    print("=" * 66)

    all_written, all_skipped, wiring = [], [], []
    verb = "would add" if args.dry_run else "added"

    # The chosen aspects, then the pieces that are not choices: a .gitignore if the
    # repo has none. Both go through the same apply(), so an existing file is still
    # never clobbered — an auto piece that is already there is simply a no-op and
    # is not reported as a skip (the user did not ask for it).
    for key in keys:
        written, skipped = aspects.apply(
            key, repo, rtype, ctx, force=args.force, dry_run=args.dry_run
        )
        for path in written:
            print(f"  [{key}] {verb} {path}")
        for path in skipped:
            print(f"  [{key}] SKIPPED {path} — already exists (use --force to replace)")
        all_written += written
        all_skipped += skipped
        for step in aspects.wiring(key, rtype):
            wiring.append((key, step))

    for key in aspects.AUTO:
        if aspects.ASPECTS[key].get("sheet"):
            continue  # the sheet is written below, once, after every token exists
        if (
            not aspects.applies(key, rtype)
            or aspects.status(key, repo, rtype) == "present"
        ):
            continue
        written, _ = aspects.apply(key, repo, rtype, ctx, dry_run=args.dry_run)
        for path in written:
            print(f"  [{key}] {verb} {path}   (always included)")
        all_written += written

    # CONFIG.md last: it lists the TODO_SET_* tokens the new files brought in, and
    # keeps whatever the sheet already had filled.
    if not args.no_config_sheet:
        if args.dry_run:
            print("  [config-sheet] would (re)generate CONFIG.md")
        else:
            # Same title the aspects were rendered with, so a sheet from `add` is
            # headed like the one the repo would have got from `new`.
            _, present = configure.generate(repo, ctx["TPLVAR_DISPLAY_NAME"])
            print(
                f"  [config-sheet] CONFIG.md — {len(present)} placeholder(s) outstanding"
            )

    _report(repo, all_written, all_skipped, wiring, notes, args.dry_run, args.force)
    return 0


# ─── Aspect selection ─────────────────────────────────────────────────────────


def _resolve_keys(requested, repo, rtype):
    """Validate the requested aspects for this repo type.

    ``None`` on bad input (caller exits non-zero); ``[]`` when there is genuinely
    nothing left to add (not an error).
    """
    if not requested:
        print(
            "ERROR: no --aspect given. Run with --detect to see what this repo is "
            "missing,\n       or --list for every aspect.",
            file=sys.stderr,
        )
        return None

    if "all" in requested:
        # "all" = bring the repo up to what {{cmd:scaffold:new}} would have produced for
        # its type. An aspect valid for the type but outside its standard set (the
        # `api` surface in an already-scaffolded api repo) stays opt-in by name.
        keys = [
            k
            for k in aspects.SELECTABLE
            if aspects.is_default(k, rtype)
            and aspects.applies(k, rtype)
            and aspects.status(k, repo, rtype) != "present"
        ]
        if not keys:
            print(
                f"Nothing to add — {repo} already has the standard set for "
                f"{_an(rtype)} repo. Add another aspect by name (--list)."
            )
        return keys

    keys = []
    for key in requested:
        if key in aspects.MERGED:
            print(
                f"ERROR: {key!r} is not a selectable aspect — {aspects.MERGED[key]}",
                file=sys.stderr,
            )
            return None
        if key not in aspects.SELECTABLE:
            print(
                f"ERROR: unknown aspect {key!r}. Choose from: "
                f"{', '.join(aspects.SELECTABLE)} (or 'all').",
                file=sys.stderr,
            )
            return None
        if not aspects.applies(key, rtype):
            ok = ", ".join(aspects.ASPECTS[key]["applies_to"])
            print(
                f"ERROR: aspect {key!r} does not apply to {_an(rtype)} repo (only: {ok}).",
                file=sys.stderr,
            )
            return None
        if key not in keys:
            keys.append(key)
    # Keep registry order so config-sheet stays last.
    return sorted(keys, key=aspects.ORDER.index)


# ─── Template values ──────────────────────────────────────────────────────────


def _build_vars(args, repo, rtype, bundle_name, bundle_uuid, keys=()):
    """Resolve every token the aspects may contain, for this repo.

    Precedence per value: CLI flag > the repo's own files > install profile >
    ``TODO_SET_*`` placeholder. Returns ``(vars, notes)`` where notes are things
    the caller must be told (e.g. a bundle uuid had to be invented) — raised only
    for the aspects that actually depend on the value.
    """
    profile, _origin = _load_profile()
    notes = []

    slug = args.slug or _slug_from_repo(repo)
    resource_key = slug.replace("-", "_")
    display_name = args.display_name or slug.replace("-", " ").title()

    def pick(arg_val, key, todo):
        return arg_val or profile.get(key) or todo

    if args.table_prefix:
        prefix_us, prefix_raw = args.table_prefix + "_", args.table_prefix
    else:
        prefix_us = prefix_raw = "TODO_SET_TABLE_PREFIX"

    # A bundle repo already has a name + uuid in databricks.yml; reuse them so
    # the pipeline's BUNDLE_TAG agree with it. Only invent them when the
    # repo has no bundle file at all, and say so.
    # Only the deploy aspect writes the bundle identity into a file (databricks.yml,
    # BUNDLE_TAG), so only it needs to hear about a missing databricks.yml.
    bundle_matters = "deploy" in keys and rtype in aspects.BUNDLE_TYPES
    if not bundle_name:
        bundle_name = f"{resource_key}_{rtype}"
        if bundle_matters:
            notes.append(
                f"No databricks.yml found — BUNDLE_TAG/bundle_name was set to "
                f"'{bundle_name}'. It must match bundle.name in your databricks.yml."
            )
    if not bundle_uuid:
        bundle_uuid = str(_uuid.uuid4()).lower()
        if bundle_matters:
            notes.append(
                f"No bundle uuid found — generated {bundle_uuid}. Put the SAME uuid in "
                f"databricks.yml (bundle.uuid); the controller identifies the bundle by it, "
                f"and it must never change after the first deploy."
            )

    org = (profile.get("org") or "").strip()
    vars_ = {
        "TPLVAR_SLUG": slug,
        "TPLVAR_RESOURCE_KEY": resource_key,
        "TPLVAR_DISPLAY_NAME": display_name,
        "TPLVAR_DESCRIPTION": args.description or "TODO_SET_DESCRIPTION",
        "TPLVAR_WORKSPACE_URL": "TODO_SET_DEV_WORKSPACE_HOST",
        "TPLVAR_CATALOG": args.catalog or "TODO_SET_CATALOG",
        "TPLVAR_TABLE_PREFIX": prefix_us,
        "TPLVAR_RAW_PREFIX": prefix_raw,
        "TPLVAR_BUNDLE_NAME": bundle_name,
        "TPLVAR_BUNDLE_UUID": bundle_uuid,
        "TPLVAR_TEAM_NAME": pick(args.team_name, "team_name", "TODO_SET_TEAM_NAME"),
        "TPLVAR_TEAM_EMAIL": pick(args.team_email, "team_email", "TODO_SET_TEAM_EMAIL"),
        "TPLVAR_TEAM_TAG": pick(args.team_name, "team_name", "TODO_SET_TEAM_NAME"),
        "TPLVAR_PROJECT": profile.get("project") or "ai-apps",  # workspace root folder
        "TPLVAR_PROJECT_TAG": slug,
        "TPLVAR_GITLAB_RUNNER": pick(
            args.gitlab_runner, "gitlab_runner", "TODO_SET_GITLAB_RUNNER"
        ),
        "TPLVAR_CONTROLLER_PROJECT_ID": pick(
            args.controller_project_id,
            "controller_project_id",
            "TODO_SET_CONTROLLER_PROJECT_ID",
        ),
        "TPLVAR_DATA_SENSITIVITY": args.data_sensitivity,
        "__ORG_PREFIX__": f"{org} " if org else "",
    }
    # Org-wide values that live as bare TODO_SET_ tokens in the templates: fill
    # from the profile when it has them, else leave the token for `configure`.
    for key, tok in _PROFILE_TODO_TOKENS.items():
        if profile.get(key):
            vars_[tok] = profile[key]
    return vars_, notes


def _slug_from_repo(repo):
    """``ai-signal-quality-etl`` -> ``signal-quality``; anything unusual is kept
    as-is (lowercased, non-alphanumerics collapsed to hyphens)."""
    name = os.path.basename(os.path.abspath(repo))
    name = _TYPE_SUFFIX_RE.sub("", name)
    name = re.sub(r"^(ai-prototype-|ai-)", "", name)
    name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return name or "service"


# ─── Output ───────────────────────────────────────────────────────────────────


def _print_list():
    print("Aspects  (--aspect KEY, repeatable; 'all' = the standard set, minus what")
    print("          the repo already has)\n")
    width = max(len(k) for k in aspects.SELECTABLE)
    for key in aspects.SELECTABLE:
        a = aspects.ASPECTS[key]
        print(f"  {key.ljust(width)}  {a['label']}")
        print(f"  {' ' * width}  {a['summary']}")
        print(f"  {' ' * width}  types: {', '.join(a['applies_to'])}\n")
    print("Always included with any add, wherever missing — never asked about:")
    # Driven by AUTO rather than written out, so an aspect added to the automatic set
    # cannot be applied by a run and missing from the list that describes the run.
    hint = {
        "standards": "docs/         the standards for this repo type, each with its conformance sheet",
        "gitignore": ".gitignore    the ignore file for this repo type (Node for fe, "
        "Python / Databricks otherwise)",
        "specs": "docs/specs/   the per-feature spec convention {{cmd:deliver:spec}} reads and writes",
        "config-sheet": "CONFIG.md     regenerated, keeping any value already filled in",
    }
    for key in aspects.AUTO:
        print("  " + hint.get(key, f"{key} — {aspects.ASPECTS[key]['summary']}"))
    print(
        "\nAn existing file is never overwritten — it is reported as SKIPPED (--force replaces)."
    )


def _an(word):
    return ("an " if word[0] in "aeiou" else "a ") + word


_STATUS_HINT = {
    "present": "already there",
    "partial": "some files present — --force to replace, or add the rest",
    "missing": "can be added",
    "n/a": "not applicable to this repo type",
}


def _print_detect(repo, rtype, type_note, bundle_name, bundle_uuid):
    print("=" * 66)
    print(f"  Repo:    {repo}")
    print(f"  Type:    {type_note}")
    if bundle_name:
        print(f"  Bundle:  {bundle_name}   uuid {bundle_uuid or '(none)'}")
    print("=" * 66)
    # The choosable aspects, with their file lists — this is what a picker offers.
    width = max(len(k) for k in aspects.SELECTABLE)
    for key in aspects.SELECTABLE:
        st = aspects.status(key, repo, rtype)
        # Standard = part of what {{cmd:scaffold:new}} gives this type. Flagging the rest
        # only matters when it is missing: it says why `all` will not pick it up.
        tag = (
            "  (not in the standard set — ask for it by name)"
            if st in ("missing", "partial") and not aspects.is_default(key, rtype)
            else ""
        )
        print(f"  {key.ljust(width)}  {st.upper():<8} {_STATUS_HINT[st]}{tag}")
        if st in ("missing", "partial"):
            print(
                f"  {' ' * width}           files: {', '.join(aspects.targets(key, rtype))}"
            )

    # Not choices — reported so the output is a complete picture of the repo.
    auto = [
        (k, aspects.status(k, repo, rtype))
        for k in aspects.AUTO
        if aspects.applies(k, rtype)
    ]
    pending = [k for k, st in auto if st != "present"]
    if pending:
        print(f"  {'(auto)'.ljust(width)}  comes with any add: {', '.join(pending)}")

    missing = [
        k
        for k in aspects.SELECTABLE
        if aspects.status(k, repo, rtype) in ("missing", "partial")
    ]
    standard = [k for k in missing if aspects.is_default(k, rtype)]
    byname = [k for k in missing if k not in standard]
    print()
    if standard:
        print(f"  Restore the standard set:  python3 add.py --repo {repo} --aspect all")
    else:
        print(f"  Standard set complete for {_an(rtype)} repo.")
    if byname:
        flags = " ".join(f"--aspect {k}" for k in byname)
        print(f"  Also available, by name:   python3 add.py --repo {repo} {flags}")
    print()


def _report(repo, written, skipped, wiring, notes, dry_run, force=False):
    print()
    if dry_run:
        print(f"  Dry run — {len(written)} file(s) would be written, nothing changed.")
    else:
        print(f"  {len(written)} file(s) written into {repo}")
    if force and written and not dry_run:
        print(
            "  Anything replaced was backed up as <name>.bak — compare, then delete "
            "the .bak files (do not commit them)."
        )
    if skipped:
        print(
            f"  {len(skipped)} left untouched (already present): {', '.join(skipped)}"
        )
    if notes:
        print("\n  Heads-up:")
        for n in notes:
            print(f"    ! {n}")
    if wiring:
        print("\n  Manual wiring the copy cannot do:")
        for key, step in wiring:
            print(f"    [{key}] {step}")
    print("\n  Then:")
    print("    1. Fill CONFIG.md and apply it:   {{cmd:scaffold:configure}}")
    print("    2. Review the added files in git before committing:  git status")
    print()


if __name__ == "__main__":
    raise SystemExit(main())
