#!/usr/bin/env python3
"""
Scaffold a new Databricks repo — one repo, one type.

A repo is exactly ONE of these types. The type picks the primary resource; CI/CD
is wired for every type.

    api    FastAPI Databricks App        resources.apps         (bundle deploy)
    etl    Lakeflow declarative pipeline resources.pipelines    (bundle deploy)
    job    Scheduled Databricks Job      resources.jobs         (bundle deploy)
    fe     React Databricks App          resources.apps         (bundle deploy)
    genie  Genie space                   resources.genie_spaces (bundle deploy)
    agent  Multi-Agent Supervisor        resources.jobs         (bundle deploy)

Note: `apps` / `jobs` / `pipelines` / `genie_spaces` are the DAB *schema
collection keys* (always plural, even for one resource). The single resource key
under them is singular.

Deployment model — ONE path, for every type:
      dev  — LOCAL dev loop:  `./run_local.sh deploy` (this laptop → dev).
      stg  — CLOUD: CI/CD controller deploys on merge to the `stg` branch.
      prod — CLOUD: CI/CD controller deploys on merge to the `prod` branch.

No type deploys itself and none holds a workspace token in CI. The controller
reaches project code only through `bundle deploy` and `bundle run`, so a repo
that ran its own deploy script would be a second, ungoverned path. What differs
between types is the payload, not the mechanism:

    fe     ships a committed dist/ — the Apps build environment cannot resolve
           registry.npmjs.org, so nothing can be built there.
    genie  ships a committed generated/space.<target>.json — the controller
           clones fresh and runs no project scripts, so the artifact is built
           locally. The catalog is baked in per target, because DAB reads a
           file_path payload verbatim.
    agent  has no DAB resource type, so the bundle's one resource is a JOB whose
           single task runs the reconciler. run_resources.yml lists it, and that
           `bundle run` IS the deploy.

Usage:
    python new.py --type {api|etl|job|fe|genie|agent} \\
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


sys.path.insert(0, _HERE)

# The composable slices of a repo (CI/CD, deploy descriptor, platform endpoints, ...).
# `new` applies them to a fresh tree; `{{cmd:scaffold:add}}` applies one to a repo that
# already exists. One registry, so an aspect means the same thing in both.
import aspects  # noqa: E402


# The profile, and the rule for WHICH profile a run uses — a project's own wins over the
# machine's (profile.py::_profile_path). Reused rather than reimplemented: this is the
# script that bakes org, team and CI controller into a repo, so it must resolve exactly
# the file {{cmd:scaffold:profile}} writes.
#
# Loaded by path rather than `import profile`, because `profile` is a stdlib module name
# and _HERE is on sys.path: a plain import would shadow the stdlib profiler for
# everything downstream of this script. Same by-path idiom profile.py uses to read its
# sibling skills' fields.
def _profile_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_scaffold_profile", os.path.join(_HERE, "profile.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


profilelib = _profile_module()

_TPL = _HERE + "/templates"
API_TPL = _TPL + "/api-skeleton"
ETL_TPL = _TPL + "/etl-bundle"
JOB_TPL = _TPL + "/job-bundle"
FE_TPL = _TPL + "/fe"


# Where scaffolded repos are created. Resolved at runtime — no hardcoded path:
#   --output-dir  >  $SCAFFOLD_OUTPUT_DIR  >  profile output_dir  >  current dir.
# The install profile ({{cmd:scaffold:profile}}) can set a default so it need not be an env
# var or flag on every run. `~` and $VARS in any source are expanded.
def _resolve_output_dir(cli_value, profile=None):
    chosen = (
        cli_value
        or os.environ.get("SCAFFOLD_OUTPUT_DIR")
        or (profile or {}).get("output_dir")
        or os.getcwd()
    )
    return os.path.expanduser(os.path.expandvars(chosen))


# Org/project profile saved by {{cmd:scaffold:profile}}. Returns the values plus where
# they came from, because "which profile" is a decision this script must not make
# silently: the same machine scaffolds for more than one client, and these values are
# the ones that differ between them.
def _load_profile(start=None):
    path, scope, shadowed = profilelib._profile_path(start)
    return profilelib.load(path), (path, scope, shadowed)


# Tool caches a formatter/linter might drop in a template dir — never copy into a repo.
_IGNORE_CACHES = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".ruff_cache", ".pytest_cache", ".DS_Store"
)

# Repo types, defined once in aspects.py (add.py needs them without importing new).
#   Every type is a bundle and every one hands stg/prod to the shared CI/CD
#   controller — see the module docstring for what differs between them.
BUNDLE_TYPES = aspects.BUNDLE_TYPES
CONTROLLER_TYPES = aspects.CONTROLLER_TYPES
ALL_TYPES = aspects.ALL_TYPES

# Resource key the controller must `bundle run` for the deploy to be complete.
# Defined in aspects.py so {{cmd:scaffold:add}} resolves the identical key — see
# aspects.run_resources_yaml for why it is a per-type fact, not a preference.
RUN_RESOURCE_BY_TYPE = aspects.RUN_RESOURCE_BY_TYPE

# Org-wide values that appear as bare TODO_SET_ tokens in templates (not TPLVAR_).
# The install profile ({{cmd:scaffold:profile}}) fills these at scaffold time when present;
# left unset, the token remains for the per-repo {{cmd:scaffold:configure}} step.
#   profile key -> template token
_PROFILE_TODO_TOKENS = {
    "owner": "TODO_SET_OWNER",
    "support_email": "TODO_SET_SUPPORT_EMAIL",
    "developers_group": "TODO_SET_DEVELOPERS_GROUP",
    # Identical for every repo in a tree, so they belong to the tree's profile
    # rather than being retyped into each repo's CONFIG.md.
    "dev_workspace_host": "TODO_SET_DEV_WORKSPACE_HOST",
    "stg_workspace_host": "TODO_SET_STG_WORKSPACE_HOST",
    "prod_workspace_host": "TODO_SET_PROD_WORKSPACE_HOST",
    "stg_service_principal": "TODO_SET_STG_SERVICE_PRINCIPAL",
    "prod_service_principal": "TODO_SET_PROD_SERVICE_PRINCIPAL",
    "stg_developers_group": "TODO_SET_STG_DEVELOPERS_GROUP",
    "prod_developers_group": "TODO_SET_PROD_DEVELOPERS_GROUP",
    "prod_admin": "TODO_SET_PROD_ADMIN_USER",
    "ci_image": "TODO_SET_CI_IMAGE",
    "policy_id": "TODO_SET_POLICY_ID",
    "dev_policy_id": "TODO_SET_DEV_POLICY_ID",
    "stg_policy_id": "TODO_SET_STG_POLICY_ID",
    "prod_policy_id": "TODO_SET_PROD_POLICY_ID",
}


def _repo_name(slug: str, rtype: str, prefix: str = "ai") -> str:
    """``<prefix>-<slug>-<type>``, adding each part only where the slug does not already say it.

    The convention puts the type in the folder name, but people slug a repo the way they say
    it out loud — "sales-api", "api-gateway", "support-agent" — and appending unconditionally
    produced ``ai-sales-api-api`` and ``ai-api-gateway-api``.

    Matched on whole hyphen-delimited **tokens**, not on substrings, and so independent of
    where in the slug the word appears. A substring test would mangle a slug like "rapid",
    whose "api" is three letters of a word and not the type at all; the token test leaves it
    alone and returns ``ai-rapid-api``. Slugs are validated as strict kebab-case below, so
    splitting on "-" is total.

    The prefix is the ``repo_prefix`` profile value, defaulting to "ai". Set it blank in the
    profile for no prefix at all, or override the whole folder name per repo with
    ``--repo-name``.
    """
    pre = [p for p in (prefix or "").split("-") if p]
    parts = [p for p in slug.split("-") if p]
    if pre and parts[: len(pre)] == pre:  # they already typed the prefix
        parts = parts[len(pre) :]
    if rtype not in parts:
        parts.append(rtype)
    return "-".join([*pre, *parts])


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

    resource_key = f"{slug}-{args.type}".replace("-", "_")

    # Org/project profile (set up via {{cmd:scaffold:profile}}; see profile.py). It fills the
    # values constant across every repo a team scaffolds. Precedence:
    #   CLI arg  >  profile  >  TODO_SET_ placeholder (left for {{cmd:scaffold:configure}}).
    # `origin` is reported in the banner — a repo is about to be stamped with an org,
    # a team and a CI controller, and which profile supplied them is not a detail.
    # An explicitly named target chooses the profile, because --output-dir (or
    # $SCAFFOLD_OUTPUT_DIR) can point into a different tree than the CWD, and the tree
    # is what decides team, CI controller and branding. Only when no target is named
    # does the CWD decide — and then the profile's own output_dir applies, so the two
    # agree by construction.
    _target = args.output_dir or os.environ.get("SCAFFOLD_OUTPUT_DIR")
    profile, origin = _load_profile(
        os.path.expanduser(os.path.expandvars(_target)) if _target else None
    )
    # If the target sits in no project at all, it resolves to the install-wide sheet —
    # which on a multi-client machine is ANOTHER client's. Working inside a project is
    # the stronger signal, so prefer its sheet over the machine's. Only a target that
    # has a project profile of its own overrides where you are standing.
    if _target and origin[1] == "global":
        cwd_profile, cwd_origin = _load_profile()
        if cwd_origin[1] == "project":
            profile, origin = cwd_profile, cwd_origin

    # Loaded before the folder name because repo_prefix comes from it. "ai" only when the
    # profile is silent; an explicit blank in the sheet means no prefix, so the lookup
    # cannot collapse "" into the default.
    prefix = profile.get("repo_prefix", "ai")
    repo_name = args.repo_name or _repo_name(slug, args.type, prefix)

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
    ws = _pick(
        args.workspace_url, "dev_workspace_host", "TODO_SET_DEV_WORKSPACE_HOST"
    ).rstrip("/")
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

    bundle_name = resource_key
    # Resource key the controller runs after deploy, per type. The token form is
    # resolved against resource_key below so this table stays declarative.
    run_resource_key = aspects.run_resource_key(args.type, resource_key)

    repo_dir = os.path.join(_resolve_output_dir(args.output_dir, profile), repo_name)
    if os.path.exists(repo_dir):
        print(
            f"ERROR: {repo_dir} already exists. Remove it or choose a different name.",
            file=sys.stderr,
        )
        sys.exit(1)

    vars_ = {
        "TPLVAR_SLUG": slug,
        "TPLVAR_APP_NAME": f"{slug}-{args.type}",
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
        "TPLVAR_PROJECT_TAG": slug.replace("-", "_"),  # per-repo bundle tag
        "TPLVAR_GITLAB_RUNNER": gitlab_runner,
        "TPLVAR_CONTROLLER_PROJECT_ID": controller_project_id,
        "TPLVAR_DATA_SENSITIVITY": args.data_sensitivity,
        "__ORG_PREFIX__": org_prefix,
    }
    # Org-wide values that live as bare TODO_SET_ tokens in templates: fill from the
    # profile only when set, otherwise leave the token for {{cmd:scaffold:configure}}.
    for key, tok in _PROFILE_TODO_TOKENS.items():
        if profile.get(key):
            vars_[tok] = profile[key]

    _banner(repo_name, repo_dir, args.type, profile, origin)

    # The type's own skeleton, then the aspects layered on top. Every aspect here
    # is the same one {{cmd:scaffold:add}} can put into a repo later — see aspects.py.
    _scaffold(args.type, repo_dir)
    vars_["TPLVAR_RUN_RESOURCE_KEY"] = run_resource_key or ""
    for key in aspects.NEW_SET_BY_TYPE[args.type]:
        _apply_aspect(key, repo_dir, args.type, vars_)

    _patch_tree(repo_dir, vars_)
    _print_next_steps(repo_dir, args.type, bundle_name, resource_key)


# ─── Scaffolding — one copytree path for every type ─────────────────────────────

# The full repo skeleton for each type lives under templates/<dir>/ (tokens intact).
# Scaffolding is: copy the dir, (etl only) drop in the generated pipeline tasks,
# make shell entrypoints executable. Controller types then get the CI/CD controller
# wired on top (see main); fe, genie and agent ship their own pipeline + deploy files.
TEMPLATE_DIR = {
    "api": API_TPL,
    "etl": ETL_TPL,
    "job": JOB_TPL,
    "fe": FE_TPL,
    "genie": _TPL + "/genie",
    "agent": _TPL + "/agent",
}


def _scaffold(rtype: str, repo_dir: str) -> None:
    src = TEMPLATE_DIR[rtype]
    # Ignore tool caches a formatter may have left in a template dir, so they
    # never leak into a scaffolded repo.
    shutil.copytree(src, repo_dir, ignore=_IGNORE_CACHES)
    print(f"  [{rtype}] copied skeleton from templates/{os.path.basename(src)}/")

    # Make any shipped shell entrypoints executable (run_local.sh).
    for fn in os.listdir(repo_dir):
        if fn.endswith(".sh"):
            os.chmod(os.path.join(repo_dir, fn), 0o755)


# ─── Aspects layered onto the skeleton ──────────────────────────────────────────

# Which aspects a fresh repo of each type gets is defined once, in aspects.py
# (NEW_SET_BY_TYPE). It is narrower than that module's DEFAULT_BY_TYPE, which is what
# {{cmd:scaffold:add}} restores: `new` writes the application code and holds back
# deploy, gitlab and specs, because none of the three can be answered correctly at
# scaffold time. See the comment on NEW_SET_BY_TYPE for the reason per aspect.


def _apply_aspect(key: str, repo_dir: str, rtype: str, vars_: dict) -> None:
    """Apply one aspect to the freshly copied skeleton, substituting tokens as it
    writes. A file the skeleton already ships is kept (aspects never clobber), so
    a type's own version of a file always wins over the shared one."""
    written, skipped = aspects.apply(key, repo_dir, rtype, vars_)
    # An aspect can write nothing — every file it owns was already shipped by the
    # skeleton. Printing a bare "[key] " line then reads as a failure.
    if written:
        shown = ", ".join(written) if len(written) <= 4 else f"{len(written)} files"
        print(f"  [{key}] {shown}")
    for path in skipped:
        print(f"  [{key}] kept the skeleton's own {path}")


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


def _banner(repo_name: str, repo_dir: str, rtype: str, profile: dict, origin) -> None:
    print("=" * 60)
    print(f"  Scaffolding: {repo_name}  (type: {rtype})")
    print(f"  Output:      {repo_dir}")
    # Which profile supplied the org, team and CI controller about to be written into
    # this repo — stated before the first file is copied, not discovered afterwards in
    # a committed databricks.yml.
    for line in profilelib.report(*origin, profile, prefix="  "):
        print(line)
    print("=" * 60)


def _print_next_steps(
    repo_dir: str, rtype: str, bundle_name: str, resource_key: str
) -> None:
    """What to do next, per type.

    Each step is a list of lines, so the numbering counts STEPS rather than
    printed lines — a two-line step is still one step.
    """
    print(f"\n  Created: {repo_dir}\n")
    print("  Next steps:")

    # No CONFIG.md step here: the placeholders it lists arrive with the deploy and
    # gitlab aspects, which this command no longer applies. It is named in the tail
    # step that adds them, where filling it is actually the next thing to do.
    steps = []
    steps += {
        "api": [
            ["schema/models.py — domain schemas; then implement routers/ + services/"],
            [
                "wheels/ — vendor the dependencies (see wheels/README.md) and COMMIT",
                "them. The Apps build environment has no network.",
            ],
        ],
        "etl": [
            ["pipeline/task*.py — implement the TODO blocks; uncomment @dp.table"],
        ],
        "job": [
            [
                "src/task_0N_*.py — implement the stages; adjust the task chain and",
                "the schedule in resources/job.job.yml",
            ],
        ],
        "fe": [
            ["pnpm install — then `pnpm ui:init` to vendor the shadcn/ui components"],
            [
                "src/app/registry.ts — one entry per feature; nav and routes both",
                "derive from it, so adding a page edits no shell file",
            ],
            [
                "dist/ — build it and COMMIT it. The Apps build cannot reach npm, so",
                "an uncommitted dist/ fails the deploy on a fresh clone.",
            ],
        ],
        "genie": [
            [
                "src/data_sources.yml — point it at your curated gold tables. Every",
                "identifier must start with ${catalog}.${schema}.",
            ],
            ["src/instructions.md — how Genie should answer (sent byte-verbatim)"],
            [
                "src/example_queries.yml — curated question -> SQL pairs. The single",
                "biggest accuracy lever a space has.",
            ],
            [
                "generated/ — `./run_local.sh all` builds it; COMMIT the result.",
                "(run_local.sh arrives with the deploy aspect — see the last step)",
            ],
        ],
        "agent": [
            [
                "src/managed/agent.yml — the tools to attach, one per tool_id. A tool",
                "NOT declared here is deleted from the live agent.",
            ],
            ["src/managed/instructions.md — routing guidance (sent byte-verbatim)"],
            [
                "./run_local.sh plan — shows what a deploy would add, change or",
                "delete, before it does it (arrives with the deploy aspect below)",
            ],
        ],
    }[rtype]

    if rtype in ("api", "genie", "agent"):
        steps.append(["Scaffold the evaluation suite with {{cmd:eval:new}}"])

    for n, lines in enumerate(steps, 1):
        print(f"    {n}. {lines[0]}")
        for cont in lines[1:]:
            print(f"       {cont}")

    _print_add_next(rtype)


# The aspects `new` holds back, as a short standing list: the command, and the one
# condition that has to be true before it is worth running. Kept separate from the
# numbered build steps above because it answers a different question — not "what do I
# write now" but "what is this repo still missing, and when do I add it".
def _print_add_next(rtype: str) -> None:
    print("\n  Then, when each prerequisite is met:")
    rows = [
        (
            "deploy",
            "databricks.yml, resources/, run_local.sh",
            "bundle name + uuid registered, stg/prod SPs created",
        ),
        (
            "gitlab",
            ".gitlab-ci.yml + setup scripts",
            "CI/CD onboarding done, group CONTROLLER_TRIGGER_TOKEN set",
        ),
    ]
    for n, (aspect, brings, when) in enumerate(rows, 1):
        print(f"    {n}. " + "{{cmd:scaffold:add}}" + f" --aspect {aspect}")
        print(f"       brings  {brings}")
        print(f"       when    {when}")
    print(
        "\n    Each add writes CONFIG.md — fill it, then apply {{cmd:scaffold:configure}}.\n"
        "    Local dev is ./run_local.sh deploy (DEV only) — stg/prod are the controller's."
    )
    print()


# ─── Pipeline reference skeletons (unchanged from the original scaffold) ─────────


if __name__ == "__main__":
    main()
