#!/usr/bin/env python3
"""Set up the org/project profile — the values that are the SAME across every repo a
team scaffolds (doc branding, workspace project, team, permissions, CI/CD, cluster
policies). Mirrors the CONFIG.md model, but ONE sheet for the whole install.

The profile is shared by every installed skill, not just this one: any sibling skill
may contribute its own fields via a ``profile_fields.py`` (see ``_sibling_fields``),
so one sheet covers the whole install and each skill still owns its own settings.

Two modes (just like /scaffold:configure):

  --generate     (Re)write ``scaffold-profile.md`` — a one-page fill-in sheet of
                 the org fields, grouped and annotated. Every field is OPTIONAL.

  (default) apply  Parse the sheet and save the filled values to
                 ``scaffold-profile.json``. ``new.py`` reads that file and bakes the
                 values into every scaffolded repo; anything left blank stays a
                 ``TODO_SET_*`` placeholder for the per-repo /scaffold:configure step.

Sheet + saved profile live in the ``.claude/`` root (two levels up from this
script), NOT in the command dir — a stray ``*.md`` there would be picked up as a
slash command, and on case-insensitive filesystems ``PROFILE.md`` would collide with
this command's ``profile.md``. One profile serves every repo you scaffold.

    python3 profile.py --generate     # write the fill-in sheet
    python3 profile.py                # apply sheet -> scaffold-profile.json
    python3 profile.py --show         # print the saved profile
"""

import argparse
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
# .claude/ root = two levels up from .claude/commands/scaffold/ (dev: repo root).
_ROOT = os.path.dirname(os.path.dirname(_HERE))
SHEET_NAME = "scaffold-profile.md"
JSON_NAME = "scaffold-profile.json"
DEFAULT_SHEET = os.path.join(_ROOT, SHEET_NAME)
DEFAULT_JSON = os.path.join(_ROOT, JSON_NAME)

# (key, group, label, example, used_in, source) — all optional. `key` is what new.py
# maps to tokens. `used_in` = where the value lands in a scaffolded repo; `source` =
# where you get the value. Both are rendered as annotations in the sheet.
FIELDS = [
    (
        "output_dir",
        "Output",
        "Where scaffolded repos are created (local path)",
        "$HOME/repos",
        "new.py output directory (local; not baked into a repo)",
        "you choose (local path; ~ and $VARS expand)",
    ),
    (
        "org",
        "Branding",
        "Organization / brand name",
        "Acme",
        "doc titles + docs/*_STANDARDS.md branding",
        "you choose (brand name)",
    ),
    (
        "project",
        "Workspace",
        "Workspace project folder — /Workspace/Shared/<project>/",
        "ai-apps",
        "databricks.yml workspace root_path + bundle.sh",
        "your Databricks workspace convention",
    ),
    (
        "team_name",
        "Team & Ownership",
        "Team name, hyphenated",
        "my-team",
        "databricks.yml team tag, .gitlab-ci.yml TEAM_TAG, team_config.yaml",
        "your team / Databricks admin (must match the team tag)",
    ),
    (
        "team_email",
        "Team & Ownership",
        "Team email",
        "team@example.com",
        "team_config.yaml + job failure alerts (resources/job.job.yml)",
        "your team",
    ),
    (
        "owner",
        "Team & Ownership",
        "Service owner",
        "Analytics",
        "API GET /v1/info (routers/platform.py)",
        "your team",
    ),
    (
        "support_email",
        "Team & Ownership",
        "Support email",
        "support@example.com",
        "API GET /v1/info (routers/platform.py)",
        "your team",
    ),
    (
        "developers_group",
        "Permissions",
        "Workspace group granted CAN_MANAGE on apps",
        "my-team-developers-dev",
        "app permissions (resources/api.app.yml)",
        "Databricks admin (workspace group name)",
    ),
    (
        "prod_admin",
        "Permissions",
        "Human owner granted CAN_MANAGE in prod",
        "you@example.com",
        "prod app permissions (databricks.yml)",
        "you / your team lead",
    ),
    (
        "controller_repo_url",
        "CI/CD",
        "CI/CD controller repo URL",
        "https://gitlab.com/<group>/databricks-asset-bundle-ci-cd-controller",
        ".gitlab-ci.yml (controller trigger)",
        "platform / DevOps team",
    ),
    (
        "gitlab_runner",
        "CI/CD",
        "GitLab runner tag for CI jobs",
        "my-ci-runner",
        ".gitlab-ci.yml (runner tag)",
        "GitLab admin / project CI settings",
    ),
    (
        "controller_project_id",
        "CI/CD",
        "CI/CD controller GitLab project id",
        "1234567",
        ".gitlab-ci.yml (trigger target)",
        "platform / DevOps team",
    ),
    (
        "ci_image",
        "CI/CD",
        "CI container image (Databricks CLI/SDK)",
        "<registry>/databricks-ci:latest",
        ".gitlab-ci.yml (job image)",
        "your container registry / platform team",
    ),
    (
        "policy_id",
        "Cluster Policies",
        "Controller cluster policy id",
        "",
        "team_config.yaml",
        "Databricks admin",
    ),
    (
        "dev_policy_id",
        "Cluster Policies",
        "Dev cluster policy id",
        "",
        "databricks.yml (dev compute)",
        "Databricks admin",
    ),
    (
        "stg_policy_id",
        "Cluster Policies",
        "Staging cluster policy id",
        "",
        "databricks.yml (stg compute)",
        "Databricks admin",
    ),
    (
        "prod_policy_id",
        "Cluster Policies",
        "Production cluster policy id",
        "",
        "databricks.yml (prod compute)",
        "Databricks admin",
    ),
]


def _sibling_fields():
    """Profile fields contributed by the OTHER skills installed alongside this one.

    The profile is shared by every skill in the install, but each skill owns its own
    fields: a skill declares them in a ``profile_fields.py`` next to its commands,
    exporting ``FIELDS`` in the same 6-tuple shape as above. They are loaded by path
    (never imported as a package) so skills stay independent — a skill that is not
    installed simply contributes nothing, and a broken one cannot break the profile.
    """
    import importlib.util

    commands_dir = os.path.dirname(_HERE)
    extra, seen = [], {f[0] for f in FIELDS}
    try:
        names = sorted(os.listdir(commands_dir))
    except OSError:
        return extra
    for name in names:
        path = os.path.join(commands_dir, name, "profile_fields.py")
        if name == os.path.basename(_HERE) or not os.path.isfile(path):
            continue
        try:
            spec = importlib.util.spec_from_file_location(
                f"_profile_fields_{name}", path
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            rows = list(getattr(mod, "FIELDS", []))
        except Exception:  # a malformed sibling must not break /scaffold:profile
            continue
        for row in rows:
            if len(row) == 6 and row[0] not in seen:
                seen.add(row[0])
                extra.append(tuple(row))
    return extra


FIELDS = FIELDS + _sibling_fields()
KEYS = {f[0] for f in FIELDS}

LINE_RE = re.compile(r"^-?\s*([a-z][a-z0-9_]*)\s*:\s*(.*)$")
TRAILING_COMMENT_RE = re.compile(r"\s+#.*$")


def load(path=DEFAULT_JSON):
    """Return the saved profile dict (only non-empty string values), or {}."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, str) and v.strip()}
    except (FileNotFoundError, ValueError):
        return {}


def generate(sheet_path=DEFAULT_SHEET, current=None):
    """Write the profile sheet. Existing values (from the saved JSON) prefill the lines.

    Two parts: a **Reference** table that defines each field (what it is, where it is
    used, where to get it), and a clean **Values** section with the fill-in lines.
    """
    current = current or {}
    lines = [
        "# Org / Project Profile",
        "",
        "Values shared by EVERY repo you scaffold. Every field is optional.",
        "",
        "1. Read the **Reference** table for what each field is, where it is used, and",
        "   where to get it.",
        "2. Fill in the ones you want in the **Values** section below (after each colon;",
        "   leave a line blank to skip it and keep that value per-repo).",
        "3. Apply with `/scaffold:profile`. Keep the keys as-is.",
        "",
        "## Reference",
        "",
        "| Field | What it is | Used in | From |",
        "|---|---|---|---|",
    ]
    for key, _grp, label, _example, used, source in FIELDS:
        lines.append(f"| `{key}` | {label} | {used or '—'} | {source or '—'} |")
    lines += ["", "## Values", ""]

    groups = []
    for f in FIELDS:
        if f[1] not in groups:
            groups.append(f[1])
    width = max(len(k) for k in KEYS) + 2
    for g in groups:
        lines.append(f"### {g}")
        for key, grp, _label, example, _used, _source in FIELDS:
            if grp != g:
                continue
            val = current.get(key, "")
            if val:
                lines.append(f"{key}: {val}")
            elif example:
                lines.append(f"{f'{key}:'.ljust(width)}# e.g. {example}")
            else:
                lines.append(f"{key}:")
        lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    with open(sheet_path, "w", encoding="utf-8") as f:
        f.write(text)
    return sheet_path


def parse(sheet_path):
    """Return ``{key: value}`` for every filled line whose key is a known field."""
    values = {}
    with open(sheet_path, encoding="utf-8") as f:
        for raw in f:
            m = LINE_RE.match(raw.strip())
            if not m:
                continue
            key = m.group(1)
            if key not in KEYS:
                continue
            val = TRAILING_COMMENT_RE.sub("", m.group(2)).strip()
            if val and not val.startswith("#"):  # skip blanks and hint-only lines
                values[key] = val
    return values


def save(values, json_path=DEFAULT_JSON):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(values, f, indent=2, sort_keys=True)
        f.write("\n")
    return json_path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Set up the org/project scaffold profile.")
    ap.add_argument(
        "--generate", action="store_true", help="(re)write PROFILE.md, then exit"
    )
    ap.add_argument(
        "--show", action="store_true", help="print the saved profile, then exit"
    )
    ap.add_argument(
        "--file", default=DEFAULT_SHEET, help="sheet path (default: PROFILE.md here)"
    )
    ap.add_argument(
        "--json",
        default=DEFAULT_JSON,
        help="saved profile path (default: org_profile.json here)",
    )
    args = ap.parse_args(argv)

    if args.show:
        prof = load(args.json)
        print(
            json.dumps(prof, indent=2, sort_keys=True) if prof else "(no profile saved)"
        )
        return 0

    if args.generate:
        path = generate(args.file, current=load(args.json))
        print(f"Wrote {path}")
        print(
            "  Fill in the fields you want (all optional), then run /scaffold:profile to save."
        )
        return 0

    if not os.path.exists(args.file):
        ap.error(f"sheet not found: {args.file}\n  run with --generate first")

    values = parse(args.file)
    if not values:
        print(
            "No filled values in the sheet — nothing saved (every field is per-repo)."
        )
        return 0
    path = save(values, args.json)
    print(f"Saved {len(values)} value(s) to {path}:")
    for k, v in sorted(values.items()):
        shown = v if len(v) <= 48 else v[:45] + "..."
        print(f"  {k:<24} -> {shown}")
    skipped = sorted(KEYS - set(values))
    if skipped:
        print(f"\n  Left per-repo ({len(skipped)}): {', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
