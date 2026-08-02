#!/usr/bin/env python3
"""Set up the org/project profile — the values that are the SAME across every repo a
team scaffolds (doc branding, workspace project, team, permissions, CI/CD, cluster
policies). Mirrors the CONFIG.md model, but ONE sheet for the whole install.

The profile is shared by every installed skill, not just this one: any sibling skill
may contribute its own fields via a ``profile_fields.py`` (see ``_sibling_fields``),
so one sheet covers the whole install and each skill still owns its own settings.

Two modes (just like {{cmd:scaffold:configure}}):

  --generate     (Re)write ``scaffold-profile.md`` — a one-page fill-in sheet of
                 the org fields, grouped and annotated. Every field is OPTIONAL.

  (default) apply  Parse the sheet and save the filled values to
                 ``scaffold-profile.json``. ``new.py`` reads that file and bakes the
                 values into every scaffolded repo; anything left blank stays a
                 ``TODO_SET_*`` placeholder for the per-repo {{cmd:scaffold:configure}} step.

Sheet + saved profile live outside the skill dir, which is replaced wholesale on every
install; a filled-in profile must survive that. They live in one of two SCOPES:

  global    the kit data dir — one profile for the whole machine
  project   <project>/__PROJECT_SCOPE_DIR__/ — one profile for one client or codebase,
            and the one that wins when you work inside that project

The scope exists because a machine serves more than one client. With only a global
profile, scaffolding inside client B's tree silently bakes client A's org, team and CI
controller into B's repo — the values are shared *across repos*, not across clients.
See ``_profile_path`` for the resolution order.

    python3 profile.py --generate                   # write the fill-in sheet
    python3 profile.py                              # apply sheet -> scaffold-profile.json
    python3 profile.py --show                       # print the resolved profile + scope
    python3 profile.py --generate --scope project   # give this project its own profile
"""

import argparse
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))

SHEET_NAME = "scaffold-profile.md"
JSON_NAME = "scaffold-profile.json"


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


def _project_scope_dir():
    """The directory name that marks a project scope — the tool's per-project config
    folder, resolved at install time because core/ must not know what any one tool calls
    its directories (§1.6).

    Empty when the token is unresolved, i.e. running from an uninstalled checkout: with
    no adapter there is no project convention to honour, so only $AGENT_KIT_PROFILE and
    the kit data dir apply. $AGENT_KIT_PROJECT_DIR is the escape hatch, and how a repo
    checkout exercises project scoping without installing.
    """
    d = os.environ.get("AGENT_KIT_PROJECT_DIR") or "__PROJECT_SCOPE_DIR__"
    return "" if d.startswith("__") else d


def _profile_path(start=None):
    """Which profile this run uses, where it came from, and what it may be shadowing.

    One machine serves more than one client, and the profile holds exactly the values
    that differ between them — org, team, CI controller, cluster policies. A single
    install-wide profile is therefore how one client's values get baked silently into
    another client's repo. So the profile is SCOPED: the nearest project profile above
    the working directory wins over the install-wide one.

        $AGENT_KIT_PROFILE                       an explicit file, for one invocation
        <dir>/<scope dir>/scaffold-profile.json  nearest project profile, walking up
        <kit data dir>/scaffold-profile.json     install-wide fallback

    Returns ``(path, scope, shadowed)``. ``scope`` is "env" | "project" | "global".
    ``shadowed`` is the nearest project scope directory that has NO profile of its own,
    or None — the caller warns on it, because "you are inside a project but using the
    machine's profile" is the case that produces a wrongly-branded repo.

    ``path`` need not exist. Every caller reports what it resolved: resolving silently
    is the actual defect, not resolving to the wrong file.
    """
    env = os.environ.get("AGENT_KIT_PROFILE")
    if env:
        return os.path.expanduser(os.path.expandvars(env)), "env", None
    root = os.path.abspath(_kit_data_dir())
    scope_name = _project_scope_dir()
    here, shadowed = os.path.abspath(start or os.getcwd()), None
    while scope_name:
        d = os.path.join(here, scope_name)
        # The kit data dir is the global fallback below, never a "project" — otherwise
        # an install into the scope directory's own name under $HOME would report itself
        # as a project profile for everything in the home tree.
        if os.path.abspath(d) != root and os.path.isdir(d):
            cand = os.path.join(d, JSON_NAME)
            if os.path.isfile(cand):
                return cand, "project", None
            shadowed = shadowed or d
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return os.path.join(root, JSON_NAME), "global", shadowed


def report(path, scope, shadowed, profile=None, prefix="  "):
    """The lines a command prints to say which profile it used, so the answer looks the
    same whichever command you ran. Sibling skills print the first line only."""
    org = (profile or {}).get("org", "")
    pad = prefix + " " * 9
    lines = [f"{prefix}profile: {scope:<7} {path}" + (f"  (org={org})" if org else "")]
    if not os.path.isfile(path):
        lines.append(pad + "no profile here — every value stays per-repo")
    if shadowed:
        lines.append(pad + "! " + shadowed + " has no profile of its own, so this")
        lines.append(pad + "  run uses the machine-wide one. Give the project its own:")
        lines.append(pad + "  {{cmd:scaffold:profile}} --generate --scope project")
    return lines


_ROOT = _kit_data_dir()
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
        "repo_prefix",
        "Branding",
        "Repo folder name prefix — <prefix>-<slug>-<type>. Blank for none",
        "ai",
        "the scaffolded repo's folder name",
        "you choose (or leave blank; --repo-name overrides per repo)",
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
        except Exception:  # a malformed sibling must not break {{cmd:scaffold:profile}}
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


def scope_dir(scope, project_dir=None):
    """The directory a given scope keeps its sheet and saved profile in.

    "project" without an explicit --project-dir means the nearest existing scope
    directory above the working directory — the same walk ``_profile_path`` does, so
    writing a profile and reading one agree on where a project starts. With no such
    directory anywhere above, one is created in the working directory and that becomes
    the project.
    """
    if scope == "global":
        return _kit_data_dir()
    name = _project_scope_dir()
    if not name:
        raise SystemExit(
            "project scope is unavailable: no adapter has resolved a project "
            "directory name. Set AGENT_KIT_PROJECT_DIR, or install the kit."
        )
    if project_dir:
        d = os.path.abspath(os.path.expanduser(os.path.expandvars(project_dir)))
        return d if os.path.basename(d) == name else os.path.join(d, name)
    root, here = os.path.abspath(_kit_data_dir()), os.getcwd()
    while True:
        d = os.path.join(here, name)
        if os.path.abspath(d) != root and os.path.isdir(d):
            return d
        parent = os.path.dirname(here)
        if parent == here:
            return os.path.join(os.getcwd(), name)
        here = parent


def ignore_in_git(dirpath):
    """Keep a project profile out of the client's repository.

    A project's scope directory is usually committed — it is where a tool's project
    instructions live. The
    profile is not that kind of file: it carries CI controller ids, runner tags, a
    workspace group and team addresses, which are the scaffolding operator's state and
    not the client's source. Appends only the lines that are missing; an existing
    .gitignore is never rewritten. Returns the path if it changed, else None.
    """
    p = os.path.join(dirpath, ".gitignore")
    existing = ""
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            existing = f.read()
    have = {ln.strip() for ln in existing.splitlines()}
    missing = [n for n in (SHEET_NAME, JSON_NAME) if n not in have]
    if not missing:
        return None
    with open(p, "a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        if existing:
            f.write("\n")
        f.write(
            "# agent-kit scaffold profile — operator state (CI ids, groups, "
            "addresses),\n# not this repo's source.\n"
        )
        f.write("\n".join(missing) + "\n")
    return p


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
        "3. Apply with `{{cmd:scaffold:profile}}`. Keep the keys as-is.",
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
        "--generate", action="store_true", help="(re)write the fill-in sheet, then exit"
    )
    ap.add_argument(
        "--show", action="store_true", help="print the resolved profile, then exit"
    )
    ap.add_argument(
        "--scope",
        choices=("auto", "project", "global"),
        default="auto",
        help="which profile to act on. auto (default) = the one this directory "
        "resolves to; project = <project>/__PROJECT_SCOPE_DIR__/, one client or "
        "codebase; "
        "global = the kit data dir, the whole machine",
    )
    ap.add_argument(
        "--project-dir",
        help="with --scope project: the project root (default: the nearest "
        "__PROJECT_SCOPE_DIR__/ "
        "above the working directory, else the working directory)",
    )
    ap.add_argument("--file", help="sheet path (overrides --scope)")
    ap.add_argument("--json", help="saved profile path (overrides --scope)")
    args = ap.parse_args(argv)

    # Resolve which profile we are acting on before doing anything, and say so. An
    # explicit --file/--json wins; --scope auto follows the same walk every consumer
    # does, so what you edit here is what {{cmd:scaffold:new}} will read from here.
    if args.scope == "auto":
        json_path, scope, shadowed = _profile_path()
        # Acting on a profile is not the same as reading one. _profile_path answers the
        # reader's question — which APPLIED profile governs here — so a project whose
        # sheet has been generated but not yet applied still resolves to global. Apply
        # in auto mode on that state and it would parse the machine's sheet and
        # overwrite the machine's profile while standing inside the project. A sheet
        # counts as the project claiming the scope, even before its first apply.
        if scope == "global":
            d = scope_dir("project")
            if os.path.isfile(os.path.join(d, SHEET_NAME)):
                json_path, scope, shadowed = os.path.join(d, JSON_NAME), "project", None
        sheet_path = os.path.join(os.path.dirname(json_path), SHEET_NAME)
    else:
        d = scope_dir(args.scope, args.project_dir)
        json_path, sheet_path, scope, shadowed = (
            os.path.join(d, JSON_NAME),
            os.path.join(d, SHEET_NAME),
            args.scope,
            None,
        )
    sheet_path = args.file or sheet_path
    json_path = args.json or json_path

    if args.show:
        prof = load(json_path)
        for line in report(json_path, scope, shadowed, prof, prefix=""):
            print(line)
        print(
            json.dumps(prof, indent=2, sort_keys=True) if prof else "(no profile saved)"
        )
        return 0

    target_dir = os.path.dirname(json_path)
    if args.generate:
        os.makedirs(target_dir, exist_ok=True)
        path = generate(sheet_path, current=load(json_path))
        print(f"Wrote {path}  (scope: {scope})")
        if scope == "project":
            ignored = ignore_in_git(target_dir)
            if ignored:
                print(
                    f"  Ignored in git via {ignored} — the profile is operator state."
                )
            print("  It wins over the machine-wide profile for anything under")
            print(f"  {os.path.dirname(target_dir)}.")
        print(
            "  Fill in the fields you want (all optional), then run {{cmd:scaffold:profile}} to save."
        )
        return 0

    if not os.path.exists(sheet_path):
        ap.error(f"sheet not found: {sheet_path}\n  run with --generate first")

    values = parse(sheet_path)
    if not values:
        print(
            "No filled values in the sheet — nothing saved (every field is per-repo)."
        )
        return 0
    os.makedirs(target_dir, exist_ok=True)
    path = save(values, json_path)
    if scope == "project":
        ignore_in_git(target_dir)
    print(f"Saved {len(values)} value(s) to {path}  (scope: {scope}):")
    for k, v in sorted(values.items()):
        shown = v if len(v) <= 48 else v[:45] + "..."
        print(f"  {k:<24} -> {shown}")
    skipped = sorted(KEYS - set(values))
    if skipped:
        print(f"\n  Left per-repo ({len(skipped)}): {', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
