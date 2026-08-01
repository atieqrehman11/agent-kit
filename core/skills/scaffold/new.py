#!/usr/bin/env python3
"""
Scaffold a new Databricks repo — one repo, one type.

A repo is exactly ONE of these types. The type picks the primary resource; CI/CD
is wired for every type.

    api    FastAPI Databricks App        resources.apps       (bundle deploy)
    etl    Lakeflow declarative pipeline resources.pipelines  (bundle deploy)
    job    Scheduled Databricks Job      resources.jobs       (bundle deploy)
    agent  Multi-Agent Supervisor        supervisor_agents API (deploy script)
    genie  Genie space                   Genie management API  (deploy script)

Note: `apps` / `jobs` / `pipelines` are the DAB *schema collection keys* (always
plural, even for one resource). The single resource key under them is singular.

Deployment model:
    Bundle types (api/etl/job):
      dev  — LOCAL dev loop:  `./bundle.sh` (this laptop → dev workspace).
      stg  — CLOUD: CI/CD controller deploys on merge to the `stg` branch.
      prod — CLOUD: CI/CD controller deploys on merge to the `prod` branch.
    agent: no bundle. src/deploy.py creates/updates an Agent Bricks Multi-Agent
      Supervisor via the supervisor_agents SDK from supervisor/ config (instructions
      + a tools list) and prints the working query URL; local via ./deploy.sh
      (CI/CD deferred).
    genie: no bundle. deploy_genie.py builds serialized_space from space.yml and
      calls the Genie createspace/updatespace API (backing-view DDL applied first);
      local via ./deploy.sh, cloud via CI on stg/prod merge.

Usage:
    python new.py --type {api|etl|job|genie|agent} \\
        --slug <kebab> --repo-name <name> --display-name "<name>" \\
        --description "<one sentence>" [--output-dir <dir>] \\
        --workspace-url <dev-url> --catalog <catalog> --table-prefix <prefix> \\
        --team-name <team> --team-email <email> \\
        [--gitlab-runner devops-ci-new] [--controller-project-id 77857303] \\
        [--data-sensitivity pii]

Output: <output-dir>/<repo-name>/
  (--output-dir, else $SCAFFOLD_OUTPUT_DIR, else profile output_dir, else CWD)
"""

import argparse
import os
import re
import shutil
import sys
import uuid

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

sys.path.insert(0, _HERE)

# The composable slices of a repo (CI/CD, standards docs, per-env config, ...).
# `new` applies them to a fresh tree; `/scaffold:add` applies one to a repo that
# already exists. One registry, so an aspect means the same thing in both.
import aspects  # noqa: E402

_TPL = _HERE + "/templates"
API_TPL = _TPL + "/api-skeleton"
ETL_TPL = _TPL + "/etl-bundle"
JOB_TPL = _TPL + "/job-bundle"


# Where scaffolded repos are created. Resolved at runtime — no hardcoded path:
#   --output-dir  >  $SCAFFOLD_OUTPUT_DIR  >  profile output_dir  >  current dir.
# The install profile (/scaffold:profile) can set a default so it need not be an env
# var or flag on every run. `~` and $VARS in any source are expanded.
def _resolve_output_dir(cli_value, profile=None):
    chosen = (
        cli_value
        or os.environ.get("SCAFFOLD_OUTPUT_DIR")
        or (profile or {}).get("output_dir")
        or os.getcwd()
    )
    return os.path.expanduser(os.path.expandvars(chosen))


# Org/project profile saved by /scaffold:profile (profile.py) next to this script.
# Returns only non-empty string values; {} when no profile has been set up.
def _load_profile():
    import json

    # Saved by /scaffold:profile in the kit data dir.
    root = _kit_data_dir()
    path = os.path.join(root, "scaffold-profile.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, str) and v.strip()}
    except (FileNotFoundError, ValueError):
        return {}


# Tool caches a formatter/linter might drop in a template dir — never copy into a repo.
_IGNORE_CACHES = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".ruff_cache", ".pytest_cache", ".DS_Store"
)

# Repo types, defined once in aspects.py (add.py needs them without importing new).
#   Bundle types deploy via `databricks bundle deploy` (dev) + the CI/CD controller
#   (stg/prod): api, etl, job.
#   Script types have no DAB bundle; a deploy script calls a Databricks management API.
#     genie: build serialized_space from space.yml → Genie createspace/updatespace API.
#     agent: a Multi-Agent Supervisor created via the supervisor_agents SDK from config
#            (instructions + a tools list) — the scripted equivalent of the Agents-tab UI.
BUNDLE_TYPES = aspects.BUNDLE_TYPES
API_TYPES = aspects.API_TYPES
ALL_TYPES = aspects.ALL_TYPES

# Org-wide values that appear as bare TODO_SET_ tokens in templates (not TPLVAR_).
# The install profile (/scaffold:profile) fills these at scaffold time when present;
# left unset, the token remains for the per-repo /scaffold:configure step.
#   profile key -> template token
_PROFILE_TODO_TOKENS = {
    "owner": "TODO_SET_OWNER",
    "support_email": "TODO_SET_SUPPORT_EMAIL",
    "developers_group": "TODO_SET_DEVELOPERS_GROUP",
    "prod_admin": "TODO_SET_PROD_ADMIN_USER",
    "controller_repo_url": "TODO_SET_CONTROLLER_REPO_URL",
    "ci_image": "TODO_SET_CI_IMAGE",
    "policy_id": "TODO_SET_POLICY_ID",
    "dev_policy_id": "TODO_SET_DEV_POLICY_ID",
    "stg_policy_id": "TODO_SET_STG_POLICY_ID",
    "prod_policy_id": "TODO_SET_PROD_POLICY_ID",
}

# ─── Entry point ──────────────────────────────────────────────────────────────


def parse_args(argv):
    p = argparse.ArgumentParser(description="Scaffold a Databricks repo.")
    p.add_argument("--type", required=True, choices=ALL_TYPES)
    p.add_argument(
        "--slug", required=True, help="kebab-case identifier, e.g. cable-health"
    )
    p.add_argument(
        "--repo-name",
        default=None,
        help="Repo folder name (default: ai-<slug>-<type>)",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Where the repo folder is created "
        "(default: $SCAFFOLD_OUTPUT_DIR, else profile output_dir, else CWD)",
    )
    p.add_argument("--display-name", required=True)
    p.add_argument("--description", required=True)
    # These four are skippable — when omitted they become TODO_SET_ placeholders
    # for the separate placeholder-fill command to resolve later.
    p.add_argument(
        "--workspace-url", default=None, help="DEV workspace URL (skippable)"
    )
    p.add_argument("--catalog", default=None, help="Unity Catalog (skippable)")
    p.add_argument("--table-prefix", default=None, help="table name prefix (skippable)")
    p.add_argument("--team-name", default=None, help="team name (skippable)")
    p.add_argument("--team-email", default=None, help="team email (skippable)")
    p.add_argument(
        "--project", default=None, help="workspace project folder (skippable)"
    )
    p.add_argument(
        "--gitlab-runner", default=None, help="GitLab runner tag (skippable)"
    )
    p.add_argument(
        "--controller-project-id",
        default=None,
        help="CI/CD controller project id (skippable)",
    )
    p.add_argument("--data-sensitivity", default="pii")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    slug = args.slug
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        print(
            f"ERROR: slug must be kebab-case (lowercase letters, digits, single "
            f"hyphens), got {slug!r}.",
            file=sys.stderr,
        )
        sys.exit(1)

    resource_key = slug.replace("-", "_")
    # Repo name carries the type as a suffix (e.g. ai-payments-api).
    repo_name = args.repo_name or f"ai-{slug}-{args.type}"

    # Org/project profile (set up once via /scaffold:profile; see profile.py). It
    # fills the values constant across every repo a team scaffolds. Precedence:
    #   CLI arg  >  install profile  >  TODO_SET_ placeholder (left for /scaffold:configure).
    profile = _load_profile()

    def _pick(arg_val, key, todo):
        return arg_val or profile.get(key) or todo

    # Per-repo skippable inputs → TODO_SET_ placeholders when omitted.
    # Two prefix forms: with trailing "_" (table names) and raw (etl tasks). When
    # unset, both stay the CLEAN placeholder — never "TODO_SET_TABLE_PREFIX_", which
    # would be an unregistered token configure can't resolve.
    if args.table_prefix:
        table_prefix_us = args.table_prefix + "_"
        table_prefix_raw = args.table_prefix
    else:
        table_prefix_us = table_prefix_raw = "TODO_SET_TABLE_PREFIX"
    catalog = args.catalog or "TODO_SET_CATALOG"
    ws = (args.workspace_url or "TODO_SET_DEV_WORKSPACE_HOST").rstrip("/")
    # Org-wide values — arg overrides profile overrides placeholder.
    team_name = _pick(args.team_name, "team_name", "TODO_SET_TEAM_NAME")
    team_email = _pick(args.team_email, "team_email", "TODO_SET_TEAM_EMAIL")
    gitlab_runner = _pick(args.gitlab_runner, "gitlab_runner", "TODO_SET_GITLAB_RUNNER")
    controller_project_id = _pick(
        args.controller_project_id,
        "controller_project_id",
        "TODO_SET_CONTROLLER_PROJECT_ID",
    )
    # Workspace project folder has a sensible generic default (not a placeholder).
    project = args.project or profile.get("project") or "ai-apps"
    # Doc-title brand prefix (blank profile → generic titles).
    org = (profile.get("org") or "").strip()
    org_prefix = f"{org} " if org else ""

    bundle_name = f"{resource_key}_{args.type}"
    # Resource key run after deploy. Deployment registers a definition; execution is
    # separate, so bundle repos are deploy-only (run on their own schedule or a manual
    # trigger). None here → run_resources.yml ships empty.
    run_resource_key = None

    repo_dir = os.path.join(_resolve_output_dir(args.output_dir, profile), repo_name)
    if os.path.exists(repo_dir):
        print(
            f"ERROR: {repo_dir} already exists. Remove it or choose a different name.",
            file=sys.stderr,
        )
        sys.exit(1)

    vars_ = {
        "TPLVAR_SLUG": slug,
        "TPLVAR_RESOURCE_KEY": resource_key,
        "TPLVAR_DISPLAY_NAME": args.display_name,
        "TPLVAR_DESCRIPTION": args.description,
        "TPLVAR_WORKSPACE_URL": ws,
        "TPLVAR_CATALOG": catalog,
        "TPLVAR_TABLE_PREFIX": table_prefix_us,  # prefix with trailing underscore
        "TPLVAR_RAW_PREFIX": table_prefix_raw,  # prefix as-is (etl pipeline tasks)
        "TPLVAR_BUNDLE_NAME": bundle_name,
        "TPLVAR_BUNDLE_UUID": str(uuid.uuid4()).lower(),
        "TPLVAR_TEAM_NAME": team_name,
        "TPLVAR_TEAM_EMAIL": team_email,
        "TPLVAR_TEAM_TAG": team_name,
        "TPLVAR_PROJECT": project,  # workspace root folder
        "TPLVAR_PROJECT_TAG": slug,  # per-repo bundle tag
        "TPLVAR_GITLAB_RUNNER": gitlab_runner,
        "TPLVAR_CONTROLLER_PROJECT_ID": controller_project_id,
        "TPLVAR_DATA_SENSITIVITY": args.data_sensitivity,
        "__ORG_PREFIX__": org_prefix,
    }
    # Org-wide values that live as bare TODO_SET_ tokens in templates: fill from the
    # profile only when set, otherwise leave the token for /scaffold:configure.
    for key, tok in _PROFILE_TODO_TOKENS.items():
        if profile.get(key):
            vars_[tok] = profile[key]

    _banner(repo_name, repo_dir, args.type)

    # The type's own skeleton, then the aspects layered on top. Every aspect here
    # is the same one /scaffold:add can put into a repo later — see aspects.py.
    _scaffold(args.type, repo_dir)
    vars_["TPLVAR_RUN_RESOURCE_KEY"] = run_resource_key or ""
    for key in aspects.DEFAULT_BY_TYPE[args.type]:
        _apply_aspect(key, repo_dir, args.type, vars_)

    _patch_tree(repo_dir, vars_)
    _write_config_sheet(repo_dir, args.display_name)
    _print_next_steps(repo_dir, args.type, bundle_name, resource_key)


# ─── Scaffolding — one copytree path for every type ─────────────────────────────

# The full repo skeleton for each type lives under templates/<dir>/ (tokens intact).
# Scaffolding is: copy the dir, (etl only) drop in the generated pipeline tasks,
# make shell entrypoints executable. Bundle types then get the CI/CD controller
# wired on top (see main); script types (genie/agent) ship their own deploy files.
TEMPLATE_DIR = {
    "api": API_TPL,
    "etl": ETL_TPL,
    "job": JOB_TPL,
    "genie": _TPL + "/genie",
    "agent": _TPL + "/agent",
}


def _scaffold(rtype: str, repo_dir: str) -> None:
    src = TEMPLATE_DIR[rtype]
    # Ignore tool caches a formatter may have left in a template dir, so they
    # never leak into a scaffolded repo.
    shutil.copytree(src, repo_dir, ignore=_IGNORE_CACHES)
    print(f"  [{rtype}] copied skeleton from templates/{os.path.basename(src)}/")

    # Make any shipped shell entrypoints executable (bundle.sh / deploy.sh).
    for fn in os.listdir(repo_dir):
        if fn.endswith(".sh"):
            os.chmod(os.path.join(repo_dir, fn), 0o755)


# ─── Aspects layered onto the skeleton ──────────────────────────────────────────

# Which aspects a fresh repo of each type gets is defined once, in aspects.py
# (DEFAULT_BY_TYPE) — the same set /scaffold:add restores in an older repo.


def _apply_aspect(key: str, repo_dir: str, rtype: str, vars_: dict) -> None:
    """Apply one aspect to the freshly copied skeleton, substituting tokens as it
    writes. A file the skeleton already ships is kept (aspects never clobber), so
    a type's own version of a file always wins over the shared one."""
    written, skipped = aspects.apply(key, repo_dir, rtype, vars_)
    shown = ", ".join(written) if len(written) <= 4 else f"{len(written)} files"
    print(f"  [{key}] {shown}")
    for path in skipped:
        print(f"  [{key}] kept the skeleton's own {path}")


def _write_config_sheet(repo_dir: str, display_name: str) -> None:
    """Emit CONFIG.md — the one-page sheet of every TODO_SET_* the repo still
    contains. Run after _patch_tree so the scan sees final, resolved content.
    Generation + apply live in configure.py (the /scaffold:configure command)."""
    import configure

    _, present = configure.generate(repo_dir, display_name)
    n = len(present)
    if n:
        print(
            f"  [config] CONFIG.md — {n} placeholder(s) to fill, then /scaffold:configure"
        )
    else:
        print("  [config] CONFIG.md — no placeholders to fill")


# ─── Placeholder patching (walk the whole tree) ─────────────────────────────────


def _patch_tree(repo_dir: str, vars_: dict) -> None:
    for root, _dirs, files in os.walk(repo_dir):
        for fn in files:
            path = os.path.join(root, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            # Only rewrite files that actually carry a token we substitute.
            if not any(m in content for m in ("TPLVAR_", "__ORG_PREFIX__")) and not any(
                tok in content for tok in vars_ if tok.startswith("TODO_SET_")
            ):
                continue
            for k, v in vars_.items():
                content = content.replace(k, v)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)


def _banner(repo_name: str, repo_dir: str, rtype: str) -> None:
    print("=" * 60)
    print(f"  Scaffolding: {repo_name}  (type: {rtype})")
    print(f"  Output:      {repo_dir}")
    print("=" * 60)


def _print_next_steps(
    repo_dir: str, rtype: str, bundle_name: str, resource_key: str
) -> None:
    print(f"\n  Created: {repo_dir}\n")
    print("  Next steps:")
    if rtype in BUNDLE_TYPES:
        print(
            "    1. CONFIG.md           — fill the placeholder sheet (hosts, service principals,"
        )
        print(
            "                             policy ids, team, repo url), then apply it with:"
        )
        print(
            "                             /scaffold:configure   (uuid is already generated)"
        )
        if rtype == "api":
            print(
                "    2. schema/models.py    — domain schemas; implement routers/ + services/"
            )
        if rtype == "etl":
            print(
                "    2. pipeline/task*.py   — implement the TODO blocks; uncomment @dp.table"
            )
        if rtype == "job":
            print(
                "    2. src/main.py         — implement run(); adjust schedule in resources/job.job.yml"
            )
        print("    3. Local dev deploy    — ./bundle.sh   (deploys to DEV only)")
        print(
            "    4. Cloud deploy        — set CONTROLLER_TRIGGER_TOKEN in GitLab CI/CD vars,"
        )
        print("                             then merge to the stg / prod branch")
    elif rtype == "agent":
        print(
            "    1. supervisor/instructions.md — write the supervisor's routing instructions"
        )
        print(
            "    2. supervisor/supervisor.yml  — set display_name/description + the tools list"
        )
        print(
            "                                    (each tool: id, type, description + its id)"
        )
        print(
            "    3. Deploy                     — ./deploy.sh   (creates/updates the supervisor,"
        )
        print(
            "                                    attaches tools, prints the working URL)"
        )
        print("    4. Scaffold evaluation with /usecase-eval:new")
    else:  # genie
        print(
            "    1. genie-space/space.yml   — set warehouse_id, description, instructions,"
        )
        print("                                 data_sources, sample_questions")
        print(
            "    2. data_sources.tables     — point at your curated gold tables (views/ is"
        )
        print(
            "                                 empty; add a bespoke view only if needed — see README)"
        )
        print(
            "    3. deploy_genie.py         — confirm the w.genie.* API calls, then uncomment"
        )
        print(
            "    4. Local deploy            — ./deploy.sh  (applies DDL + create/update space)"
        )
        print(
            "    5. Cloud deploy            — merge to the stg / prod branch (CI runs deploy_genie.py)"
        )
        print("    6. Scaffold evaluation with /usecase-eval:new")
    print()


# ─── Pipeline reference skeletons (unchanged from the original scaffold) ─────────


if __name__ == "__main__":
    main()
