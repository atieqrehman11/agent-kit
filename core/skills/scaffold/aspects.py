"""Composable repo **aspects** — the slices a repo is made of, one at a time.

An *aspect* is a named, self-contained piece of a scaffolded repo: its CI/CD
pipeline, its standards docs, its per-environment config, the platform endpoints
every API must expose. ``new.py`` applies several when it creates a repo from
scratch; ``add.py`` applies one to a repo that **already exists**. Both go
through :func:`apply` here, so "the cicd aspect" means exactly the same set of
files in a brand-new repo and in a five-year-old one.

Each entry is::

    key: {
      "label":      short name shown in pickers,
      "summary":    one line — what the repo gains,
      "applies_to": repo types the aspect is valid for,
      "files":      template file -> repo path       (per-type or "*"),
      "dirs":       template dir  -> repo dir        (per-type or "*"),
      "generated":  repo path <- callable(vars) -> text,
      "wiring":     manual steps a file copy cannot do (per-type or "*"),
    }

``files`` / ``dirs`` / ``generated`` / ``wiring`` may each be a plain list (same
for every type) or a dict keyed by repo type with a ``"*"`` fallback.

Adding an aspect is one entry here — both commands pick it up, and `add.py
--detect` reports its status against any repo without further wiring.
"""

import os
import re
import shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(_HERE, "templates")


def _guidelines_dir():
    """The shared guidelines dir. The *_STANDARDS docs a scaffolded repo receives are
    guidelines, not templates — one source of truth, read from here rather than copied."""
    d = os.environ.get("AGENT_KIT_GUIDELINES_DIR") or "__GUIDELINES_DIR__"
    if not d.startswith("__"):
        return d
    p = _HERE
    while p != os.path.dirname(p):
        if os.path.exists(os.path.join(p, "STANDARD.md")):
            return os.path.join(p, "core", "guidelines")
        p = os.path.dirname(p)
    return os.path.join(_HERE, "templates")


GUIDELINES = _guidelines_dir()


def _src_path(src_rel):
    """Resolve a files-tuple source. ``guidelines:<name>`` reads the shared guideline."""
    if src_rel.startswith("guidelines:"):
        return os.path.join(GUIDELINES, src_rel.split(":", 1)[1])
    return os.path.join(TEMPLATES, src_rel)


def _strip_frontmatter(text):
    m = re.match(r"\A---\n.*?\n---\n+", text, re.S)
    return text[m.end() :] if m else text


# Repo types, mirrored from new.py (kept here so add.py needs only this module).
# Bundle types deploy with `databricks bundle deploy`; of those, the controller
# types hand stg/prod to the shared DAB CI/CD controller. `fe` is a bundle type
# that is NOT a controller type: what it deploys is a build artifact (dist/), the
# controller deploys from a git checkout and runs no Node build, and dist/ must
# not be committed — so building and deploying have to happen in one job, which
# is the job in the repo's own pipeline.
BUNDLE_TYPES = ("api", "etl", "job", "fe")
CONTROLLER_TYPES = ("api", "etl", "job", "fe")
API_TYPES = ("genie", "agent")
ALL_TYPES = BUNDLE_TYPES + API_TYPES

# Per-type standards doc: repo type -> (template file, filename under docs/).
STANDARDS = {
    "api": ("guidelines:api.md", "API_STANDARDS.md"),
    "etl": ("guidelines:pipeline.md", "PIPELINE_STANDARDS.md"),
    "job": ("guidelines:job.md", "JOB_STANDARDS.md"),
    "fe": ("guidelines:react.md", "REACT_STANDARDS.md"),
    "agent": ("guidelines:agent.md", "AGENT_STANDARDS.md"),
    "genie": ("guidelines:genie.md", "GENIE_STANDARDS.md"),
}

# Repo types that contain a request boundary and therefore hand-written service
# code — these get the service-structure standard alongside their own.
SERVICE_TYPES = ("api", "job")

# Types whose baseline language standard is Python. `fe` is TypeScript end to
# end — server.mjs included — so shipping it PYTHON_STANDARDS.md would be a doc
# nobody in that repo can act on.
PYTHON_TYPES = tuple(t for t in ALL_TYPES if t != "fe")


def _conformance_for(src_rel, dest):
    """The ``conformance/<name>.md`` checklist of a guideline, if it has one (STANDARD.md §1.2).

    Derived from the tree rather than listed: a guideline that gains a sheet starts
    shipping it with no edit here, which is the same rule obligation 1 puts on adapters.

    The generated repo gets a flat ``docs/<NAME>_CONFORMANCE.md`` rather than a mirrored
    directory — a use-case repo carries one or two of these, so a folder holding a single
    file would be structure for its own sake.
    """
    if not src_rel.startswith("guidelines:"):
        return []
    name = src_rel.split(":", 1)[1][:-3]
    if not os.path.isfile(os.path.join(GUIDELINES, "conformance", f"{name}.md")):
        return []
    return [(f"guidelines:conformance/{name}.md", f"docs/{dest[:-3]}_CONFORMANCE.md")]


# Tool caches a formatter/linter may have dropped in a template dir.
_IGNORE = {"__pycache__", ".ruff_cache", ".pytest_cache", ".DS_Store"}


# ─── Generated file bodies ────────────────────────────────────────────────────


def run_resources_yaml(vars_) -> str:
    """``run_resources.yml`` — resource keys the controller runs after deploy.

    Deployment only registers a definition; execution is separate, so this ships
    empty for deploy-only bundles. ``vars_["TPLVAR_RUN_RESOURCE_KEY"]`` (when
    set) lists a key that must run to complete the deploy.
    """
    header = (
        "# Resource keys the controller runs immediately after deploy.\n"
        "# Deployment only registers a definition — execution is separate. Leave\n"
        "# empty for deploy-only bundles (an app starts itself; a job/pipeline runs\n"
        "# on its own schedule or a manual trigger). List a key here only to force\n"
        "# a run after every deploy.\n"
    )
    key = (vars_ or {}).get("TPLVAR_RUN_RESOURCE_KEY", "")
    if key:
        return f"{header}resources:\n  - {key}\n"
    return f"{header}resources: []\n  # e.g. - my_resource_key   # uncomment to run after deploy\n"


# ─── The registry ─────────────────────────────────────────────────────────────

# Wiring notes are *manual* steps: things a file copy provably cannot do, such as
# editing a databricks.yml or an app.py the repo already owns. They are printed
# after an apply and are the honest boundary of what the script did.
_CICD_WIRING = [
    "Run cicd/setup-gitlab-project.sh --group <id> to create dev/stg/prod, set "
    "branch protection and the default branch, add the controller to the "
    "job-token allowlist, and put CONTROLLER_TRIGGER_TOKEN on the group. It is a "
    "dry run until --apply. stg and prod must stay PROTECTED branches or the "
    "trigger silently receives an empty token.",
    "Confirm BUNDLE_TAG in .gitlab-ci.yml matches bundle.name in databricks.yml, "
    "and that team_config.yaml's bundle_name + uuid match it too. A mismatch "
    "fails the controller's governance stage, not your pipeline.",
    "Submit team_config.yaml to the platform team, including the service "
    "principal ids. The controller reads run_as out of databricks.yml and fails "
    "governance if it is missing on stg/prod.",
]

# genie/agent deploy through a management API, so they need workspace credentials
# rather than a controller token. Per-branch scoping is what separates stg from prod.
_API_TYPE_CICD_WIRING = [
    "Set DATABRICKS_HOST + DATABRICKS_TOKEN in GitLab > Settings > CI/CD > "
    "Variables (masked), scoped to the `stg` and `prod` branches separately — the "
    "deploy job authenticates with them, and the workspace is what separates the "
    "environments.",
    "Push the `stg` / `prod` branches — the deploy job is manual on each.",
]

# fe deploys through the controller like the other bundle types. What is
# different is what it ships: a prebuilt dist/ rather than source, because the
# Apps build environment cannot resolve registry.npmjs.org.
_FE_CICD_WIRING = [
    "Commit dist/. `./run_local.sh deploy` builds it; the controller deploys from "
    "a fresh clone, so an uncommitted dist/ means `validate_bundle` fails with "
    "`stat dist: no such file or directory`.",
    "Rebuild and commit dist/ whenever src/ changes. Nothing enforces this — a "
    "stale dist/ deploys green and serves the previous bundle.",
    "Confirm resources/fe.app.yml keeps package.json out of the app root. If it "
    "reaches the workspace the platform runs an install, which fails with "
    "`EAI_AGAIN registry.npmjs.org`.",
]

_ENV_CONFIG_WIRING = [
    "Add the config_dir + policy_id variables to databricks.yml and set them per "
    "target (the resource then reads ${var.config_dir}/task_config.yaml):\n"
    "        variables:\n"
    "          config_dir:\n"
    '            description: "Per-target config directory (config/DEV|STG|PROD)"\n'
    '            default: ""\n'
    "          policy_id:\n"
    '            default: "TODO_SET_DEV_POLICY_ID"\n'
    "        targets:\n"
    "          dev:  { variables: { config_dir: ${workspace.file_path}/config/DEV,  "
    "policy_id: TODO_SET_DEV_POLICY_ID } }\n"
    "          stg:  { variables: { config_dir: ${workspace.file_path}/config/STG,  "
    "policy_id: TODO_SET_STG_POLICY_ID } }\n"
    "          prod: { variables: { config_dir: ${workspace.file_path}/config/PROD, "
    "policy_id: TODO_SET_PROD_POLICY_ID } }",
    "Pass the config path to your task, e.g. a job task's parameters: "
    '["--config", "${var.config_dir}/task_config.yaml"].',
]

_API_PLATFORM_WIRING = [
    "Wire the router into your FastAPI app:  from routers import platform  →  "
    "app.include_router(platform.router)",
    "Check core/config.py — service_id / display_name / description feed GET /v1/info. "
    "If the repo already had its own config module, merge into Settings and delete the "
    "other one; two config modules means two answers to the same question.",
    "Configure logging once at startup, from settings:  "
    "configure_logging(settings.log_level, settings.log_format, settings.service_id)  — "
    "then remove any basicConfig / setLevel elsewhere, or LOG_LEVEL stops working.",
    "Add the request context middleware:  "
    "app.add_middleware(RequestContextMiddleware, service_id=settings.service_id)  — "
    "it generates and echoes X-Request-ID and emits the one access-log line "
    "(docs/API_STANDARDS.md §10).",
    "Register the exception handlers:  register_exception_handlers(app)  — this is what "
    "normalizes FastAPI's {'detail': ...} onto the ErrorResponse envelope and installs the "
    "catch-all (docs/API_STANDARDS.md §7). Then delete any per-route error bodies.",
    "Raise from core/exceptions.py in services and repositories — never HTTPException "
    "below the router (docs/SERVICE_STRUCTURE_STANDARDS.md §3).",
    "Set CORS from settings.cors_origins — an allowlist, never ['*'].",
]

ASPECTS = {
    # ── The two aspects a user picks ─────────────────────────────────────────
    "cicd": {
        "label": "CI/CD pipeline",
        "summary": (
            "The whole deploy story: bundle descriptor, resource definitions, pipeline "
            "and registry entry. api/etl/job/fe deploy through the shared DAB "
            "controller (+ the per-environment config a job reads); genie/agent "
            "validate their declaration, then run their own deploy script"
        ),
        "applies_to": ALL_TYPES,
        "selectable": True,
        # This aspect owns the whole deploy story: the bundle descriptor, the
        # resource definitions, the pipeline and the registry entry. The type
        # skeletons ship application code only, so `new` cannot produce a repo
        # whose deploy config disagrees with its pipeline.
        "files": {
            "api": [
                ("cicd/gitlab-ci.controller.yml", ".gitlab-ci.yml"),
                ("cicd/team_config.yaml", "team_config.yaml"),
                ("cicd/bundleignore", ".bundleignore"),
                ("cicd/api/databricks.yml", "databricks.yml"),
                ("cicd/api/app.yml", "app.yml"),
                ("cicd/api/bundle.sh", "bundle.sh"),
            ],
            "etl": [
                ("cicd/gitlab-ci.controller.yml", ".gitlab-ci.yml"),
                ("cicd/team_config.yaml", "team_config.yaml"),
                ("cicd/bundleignore", ".bundleignore"),
                ("cicd/etl/databricks.yml", "databricks.yml"),
                ("cicd/etl/bundle.sh", "bundle.sh"),
            ],
            "job": [
                ("cicd/gitlab-ci.controller.yml", ".gitlab-ci.yml"),
                ("cicd/team_config.yaml", "team_config.yaml"),
                ("cicd/bundleignore", ".bundleignore"),
                ("cicd/job/databricks.yml", "databricks.yml"),
                ("cicd/job/bundle.sh", "bundle.sh"),
            ],
            # fe deploys through the controller like the others. It ships a
            # prebuilt dist/ rather than source, because the Apps build
            # environment cannot reach the npm registry — see cicd/fe/databricks.yml.
            "fe": [
                ("cicd/gitlab-ci.controller.yml", ".gitlab-ci.yml"),
                ("cicd/team_config.yaml", "team_config.yaml"),
                ("cicd/fe/databricks.yml", "databricks.yml"),
                ("cicd/fe/run_local.sh", "run_local.sh"),
            ],
            # Neither is a DAB resource, so neither triggers the controller. Their
            # jobs invoke src/validate.py and src/deploy.py, so the aspect ships
            # those too — otherwise `add` installs a pipeline pointing at missing
            # files.
            "genie": [
                ("cicd/genie/.gitlab-ci.yml", ".gitlab-ci.yml"),
                ("cicd/genie/deploy.sh", "deploy.sh"),
                ("cicd/genie/src/validate.py", "src/validate.py"),
                ("cicd/genie/src/deploy.py", "src/deploy.py"),
            ],
            "agent": [
                ("cicd/agent/.gitlab-ci.yml", ".gitlab-ci.yml"),
                ("cicd/agent/deploy.sh", "deploy.sh"),
                ("cicd/agent/src/validate.py", "src/validate.py"),
                ("cicd/agent/src/deploy.py", "src/deploy.py"),
            ],
        },
        # config/{DEV,STG,PROD} is part of the deploy story, not a thing to choose
        # separately: the DEV/STG/PROD split exists *because* the controller deploys
        # per target. Only `job` reads it (${var.config_dir}/task_config.yaml) — api
        # serves env from app.yml and etl bakes the catalog into its tasks, so
        # shipping config/ for them would be dead weight.
        "dirs": {
            "api": [("cicd/api/resources", "resources")],
            "etl": [("cicd/etl/resources", "resources")],
            "job": [("cicd/job/resources", "resources"), ("cicd/config", "config")],
            "fe": [("cicd/fe/resources", "resources")],
            "*": [],
        },
        # run_resources.yml tells the CONTROLLER what to run after deploy, so it
        # is meaningless in a repo that does not use the controller.
        "generated": {
            "*": [("run_resources.yml", run_resources_yaml)],
            "genie": [],
            "agent": [],
        },
        "wiring": {
            "*": _CICD_WIRING,
            "job": _CICD_WIRING + _ENV_CONFIG_WIRING,
            "fe": _FE_CICD_WIRING,
            "genie": _API_TYPE_CICD_WIRING
            + [
                "Run `python src/validate.py` before pushing — it is exactly what the "
                "pipeline's first stage runs, and it needs no credentials. A repo that "
                "predates this pipeline usually fails on one thing: a `space_id:` left "
                "in genie-space/space.yml. Delete it. The space is resolved by title, "
                "so a committed id is deploy state the repo must not hold.",
                "If the repo already had a deploy_genie.py at its root, delete it — "
                "src/deploy.py replaces it, and two deploy scripts means two answers "
                "to which space this repo owns.",
            ],
            "agent": _API_TYPE_CICD_WIRING
            + [
                "Run `python src/validate.py` before pushing — it is exactly what the "
                "pipeline's first stage runs, and it needs no credentials. A repo that "
                "predates this pipeline usually fails on one thing: a "
                "`supervisor_agent_id:` left in supervisor/supervisor.yml. Delete it. "
                "The supervisor is resolved by name, so a committed id is deploy state "
                "the repo must not hold.",
            ],
        },
    },
    "api": {
        "label": "Use case API surface",
        "summary": (
            "GET /v1/health and GET /v1/info (API_STANDARDS §3–4), plus the service "
            "spine they need: validated settings, one logging setup, one exception "
            "hierarchy behind one handler layer, and request-id middleware "
            "(SERVICE_STRUCTURE_STANDARDS §2–4)"
        ),
        "applies_to": ("api",),
        "selectable": True,
        # The platform endpoints alone are not installable — they read Settings, and
        # their error path is the handler layer. Shipping the routers without the
        # spine would produce a repo that fails its own conformance checklist on
        # day one, which is how the previous version of this aspect behaved.
        "files": [
            ("api-skeleton/routers/__init__.py", "routers/__init__.py"),
            ("api-skeleton/routers/platform.py", "routers/platform.py"),
            ("api-skeleton/core/__init__.py", "core/__init__.py"),
            ("api-skeleton/core/config.py", "core/config.py"),
            ("api-skeleton/core/logging_setup.py", "core/logging_setup.py"),
            ("api-skeleton/core/exceptions.py", "core/exceptions.py"),
            ("api-skeleton/core/handlers.py", "core/handlers.py"),
            ("api-skeleton/core/middleware.py", "core/middleware.py"),
            ("api-skeleton/schema/__init__.py", "schema/__init__.py"),
            ("api-skeleton/schema/models.py", "schema/models.py"),
            ("api-skeleton/services/__init__.py", "services/__init__.py"),
            ("api-skeleton/repositories/__init__.py", "repositories/__init__.py"),
        ],
        "wiring": _API_PLATFORM_WIRING,
    },
    # ── Not choices: pieces every repo just has ───────────────────────────────
    # `standards` ships with `new` (each type's docs/), and `gitignore` /
    # `config-sheet` are applied automatically wherever they are missing. They are
    # in the registry so there is still one definition of each, but they never
    # appear in a picker — nobody should have to decide about them.
    "standards": {
        "label": "Standards docs",
        "summary": (
            "docs/PYTHON_STANDARDS.md + the per-type <TYPE>_STANDARDS.md, "
            "plus docs/SERVICE_STRUCTURE_STANDARDS.md wherever service code is written"
        ),
        "applies_to": ALL_TYPES,
        "selectable": False,
        "files": {
            t: [(src, f"docs/{dest}")]
            + (
                [("guidelines:python.md", "docs/PYTHON_STANDARDS.md")]
                if t in PYTHON_TYPES
                else []
            )
            # A guideline's checklist lives in a sibling now (STANDARD.md §1.2), so the
            # standards doc alone would land in the repo without its audit list.
            + _conformance_for(src, dest)
            # Layering, exception handling, log levels and the no-hardcoded-values
            # rule only bind a repo that has a request boundary. A genie space is
            # configuration; shipping it a service standard is noise.
            + (
                [
                    (
                        "guidelines:service-structure.md",
                        "docs/SERVICE_STRUCTURE_STANDARDS.md",
                    )
                ]
                + _conformance_for(
                    "guidelines:service-structure.md",
                    "SERVICE_STRUCTURE_STANDARDS.md",
                )
                if t in SERVICE_TYPES
                else []
            )
            for t, (src, dest) in STANDARDS.items()
        },
    },
    "gitignore": {
        "label": "Python / Databricks .gitignore",
        "summary": "the shared .gitignore (venvs, .databricks/, build + deploy artifacts)",
        "applies_to": ALL_TYPES,
        "selectable": False,
        # fe gets a Node one. The shared file ignores dist/ as build junk, which
        # is right everywhere except here, where dist/ is the deployed payload —
        # still not committed, but for a different reason, and the file says so.
        "files": {
            "*": [("common/gitignore", ".gitignore")],
            "fe": [("fe/.gitignore", ".gitignore")],
        },
    },
    # A convention needs somewhere to land before the first feature, or the first
    # spec gets written wherever that run happened to guess. One README, no
    # placeholder feature folder — an empty example folder is the kind of thing
    # people copy rather than replace.
    "specs": {
        "label": "docs/specs/ convention",
        "summary": (
            "one README explaining the per-feature spec folder "
            "(requirements / design / tasks / report) the deliver skill reads and writes"
        ),
        "applies_to": ALL_TYPES,
        "selectable": False,
        "files": [("common/specs-README.md", "docs/specs/README.md")],
    },
    "config-sheet": {
        "label": "CONFIG.md placeholder sheet",
        "summary": (
            "one page listing every TODO_SET_* the repo still contains, "
            "for {{cmd:scaffold:configure}} to apply"
        ),
        "applies_to": ALL_TYPES,
        "selectable": False,
        # Written through configure.generate() (it must run last, after the other
        # aspects have introduced their tokens), so no files here.
        "sheet": True,
    },
}

# Apply order. config-sheet is last on purpose: it must see the tokens the other
# aspects bring in.
ORDER = ["cicd", "api", "standards", "gitignore", "specs", "config-sheet"]

# What a user chooses between. Everything else in ASPECTS is applied for them.
SELECTABLE = [k for k in ORDER if ASPECTS[k].get("selectable")]

# Applied automatically by `add` after the chosen aspects, wherever missing — no
# question asked, no menu entry. Order matters: config-sheet last.
# Applied on every add, not just on new. `standards` is here because the aspects that
# ship code ship code that *cites* the standards: the api aspect alone writes ten
# references to docs/API_STANDARDS.md and docs/SERVICE_STRUCTURE_STANDARDS.md, in
# docstrings and in the printed wiring notes. Without this, adding it to a repo the
# scaffold never created produced a repo with no docs/ and ten dangling pointers — the
# same broken-link class STANDARD.md §1.6.1 refuses for command references.
# Safe on a repo that already has them: _emit skips an existing file rather than
# overwriting it, so a doc someone has edited survives.
AUTO = ["standards", "gitignore", "specs", "config-sheet"]

# Keys that are not choices, mapped to where that work lives now — so anyone who
# reaches for one gets a pointer instead of "unknown aspect".
MERGED = {
    "env-config": "config/{DEV,STG,PROD} now ships with the `cicd` aspect on job repos.",
    "api-platform": "it is now called `api`.",
    "standards": "standards docs ship with {{cmd:scaffold:new}}, per repo type.",
    "gitignore": ".gitignore is applied automatically wherever it is missing.",
    "specs": "docs/specs/README.md is applied automatically wherever it is missing.",
    "config-sheet": "CONFIG.md is regenerated automatically after every add.",
}

# The **standard set** per type: what a repo of this type gets from `new`, and so
# what `add --aspect all` restores in a repo that predates the scaffold. Notes:
#   cicd  — controller types get the controller pipeline (job also gets config/).
#           fe, genie and agent each ship their own .gitlab-ci.yml inside their
#           template dir, so `new` does not layer the aspect on top; `add` still
#           can, for a repo that predates it.
#   api   — part of the api skeleton already, so not layered again by `new`; the
#           aspect exists for FastAPI repos that were never scaffolded.
# README.md ships inside each template dir (tokens patched by new.py's _patch_tree).
DEFAULT_BY_TYPE = {
    "api": ("cicd", "standards", "gitignore", "specs"),
    "etl": ("cicd", "standards", "gitignore", "specs"),
    "job": ("cicd", "standards", "gitignore", "specs"),
    "fe": ("cicd", "standards", "gitignore", "specs"),
    "agent": ("cicd", "standards", "gitignore", "specs"),
    "genie": ("cicd", "standards", "gitignore", "specs"),
}


def is_default(key, rtype):
    """Is this aspect part of the standard set for ``rtype``?"""
    return key in DEFAULT_BY_TYPE.get(rtype, ()) or key in AUTO


# ─── Resolution helpers ───────────────────────────────────────────────────────


def _for_type(entry, rtype):
    """A per-type-or-``*`` field, resolved to a list for ``rtype``."""
    if entry is None:
        return []
    if isinstance(entry, dict):
        return list(entry.get(rtype, entry.get("*", [])))
    return list(entry)


def applies(key, rtype):
    return rtype in ASPECTS[key]["applies_to"]


def wiring(key, rtype):
    return _for_type(ASPECTS[key].get("wiring"), rtype)


def targets(key, rtype):
    """Every repo-relative path the aspect writes, in write order.

    Directories are expanded to their real files, so ``--detect`` and the
    skip-existing logic work per file rather than per directory.
    """
    out = []
    for _src, dest in _for_type(ASPECTS[key].get("files"), rtype):
        out.append(dest)
    for src_dir, dest_dir in _for_type(ASPECTS[key].get("dirs"), rtype):
        for src, dest in _walk_dir(os.path.join(TEMPLATES, src_dir), dest_dir):
            out.append(dest)
    for dest, _fn in _for_type(ASPECTS[key].get("generated"), rtype):
        out.append(dest)
    return out


def _walk_dir(src_root, dest_root):
    """Yield ``(abs_src_file, repo_relative_dest)`` for a template directory."""
    pairs = []
    for root, dirs, files in os.walk(src_root):
        dirs[:] = sorted(d for d in dirs if d not in _IGNORE)
        for fn in sorted(files):
            if fn in _IGNORE:
                continue
            src = os.path.join(root, fn)
            rel = os.path.relpath(src, src_root)
            pairs.append((src, os.path.join(dest_root, rel)))
    return pairs


def status(key, repo_dir, rtype):
    """``"n/a"`` | ``"missing"`` | ``"partial"`` | ``"present"`` for a repo."""
    if not applies(key, rtype):
        return "n/a"
    if ASPECTS[key].get("sheet"):
        return (
            "present"
            if os.path.exists(os.path.join(repo_dir, "CONFIG.md"))
            else "missing"
        )
    paths = targets(key, rtype)
    if not paths:
        return "missing"
    have = sum(1 for p in paths if os.path.exists(os.path.join(repo_dir, p)))
    if have == 0:
        return "missing"
    return "present" if have == len(paths) else "partial"


# ─── Apply ────────────────────────────────────────────────────────────────────


def apply(key, repo_dir, rtype, vars_, force=False, dry_run=False):
    """Write one aspect into ``repo_dir``.

    Existing files are **never** silently overwritten: without ``force`` they are
    skipped and reported; with ``force`` the previous file is kept as
    ``<name>.bak`` first. Only files this aspect writes are touched — nothing
    else in the repo is read or rewritten, which is what makes the command safe
    on a repo it did not create.

    Returns ``(written, skipped)`` — both lists of repo-relative paths.
    """
    if not applies(key, rtype):
        raise ValueError(f"aspect {key!r} does not apply to a {rtype!r} repo")

    written, skipped = [], []

    def _emit(dest_rel, text=None, src=None):
        dest = os.path.join(repo_dir, dest_rel)
        if os.path.exists(dest) and not force:
            skipped.append(dest_rel)
            return
        if dry_run:
            written.append(dest_rel)
            return
        if os.path.exists(dest) and force:
            shutil.copy2(dest, dest + ".bak")
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        if text is None:
            text = _read(src)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(substitute(text, vars_))
        # Entrypoints are aspect-owned now, and a fresh file is 0644 — a
        # run_local.sh nobody can run is a scaffold that does not work.
        if dest_rel.endswith(".sh"):
            os.chmod(dest, 0o755)
        written.append(dest_rel)

    for src_rel, dest_rel in _for_type(ASPECTS[key].get("files"), rtype):
        if src_rel.startswith("guidelines:"):
            _emit(dest_rel, text=_strip_frontmatter(_read(_src_path(src_rel))))
        else:
            _emit(dest_rel, src=_src_path(src_rel))

    for src_dir, dest_dir in _for_type(ASPECTS[key].get("dirs"), rtype):
        for src, dest_rel in _walk_dir(os.path.join(TEMPLATES, src_dir), dest_dir):
            _emit(dest_rel, src=src)

    for dest_rel, fn in _for_type(ASPECTS[key].get("generated"), rtype):
        _emit(dest_rel, text=fn(vars_))

    return written, skipped


def substitute(text, vars_):
    """Replace template tokens. Longest key first so a token that is a prefix of
    another (``TPLVAR_ENDPOINT`` vs ``TPLVAR_ENDPOINT_HINT``) stays intact."""
    for k in sorted(vars_ or {}, key=len, reverse=True):
        text = text.replace(k, vars_[k])
    return text


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ─── Repo-type detection ──────────────────────────────────────────────────────


# Evidence that names a repo's type, most specific first. Each entry is
# (type, reason, predicate on the repo dir).
def detect_type(repo_dir):
    """Best-effort ``(type, reason)`` for an existing repo; ``(None, reason)``
    when nothing decisive is found (the caller then requires ``--type``)."""
    j = lambda *p: os.path.join(repo_dir, *p)  # noqa: E731

    if os.path.isfile(j("genie-space", "space.yml")):
        return "genie", "genie-space/space.yml"
    if os.path.isfile(j("supervisor", "supervisor.yml")):
        return "agent", "supervisor/supervisor.yml"

    # Checked BEFORE the resource-file scan below: a front end is also an
    # `apps` resource, so `.app.yml` alone cannot tell it from an api repo. A
    # package.json next to a Vite config can.
    if os.path.isfile(j("package.json")):
        for fn in ("vite.config.ts", "vite.config.js", "vite.config.mts"):
            if os.path.isfile(j(fn)):
                return "fe", f"package.json + {fn}"

    # A bundle repo naming its resource in resources/<key>.<kind>.yml.
    res = _resource_files(repo_dir)
    for suffix, rtype in (
        (".app.yml", "api"),
        (".pipeline.yml", "etl"),
        (".job.yml", "job"),
    ):
        hit = next((f for f in res if f.endswith(suffix)), None)
        if hit:
            return rtype, f"resources/{hit}"

    # Or declaring resources inline in databricks.yml — the DAB collection key
    # (always plural) names the type just as well as a separate resource file.
    for key, rtype in (("apps:", "api"), ("pipelines:", "etl"), ("jobs:", "job")):
        if _declares(repo_dir, key):
            return rtype, f"databricks.yml resources.{key.rstrip(':')}"

    for fn in ("app.yml", "app.yaml", "app.py"):
        if os.path.isfile(j(fn)):
            return "api", fn
    if os.path.isdir(j("pipeline")):
        return "etl", "pipeline/"

    # Fall back to the repo-name suffix the scaffold gives every repo.
    name = os.path.basename(os.path.abspath(repo_dir))
    for t in ALL_TYPES:
        if name.endswith("-" + t):
            return t, f"repo name suffix -{t}"
    return None, "no decisive marker found"


def _declares(repo_dir, collection_key):
    """Does ``databricks.yml`` declare this resource collection inline?

    Matched as an indented key (``  apps:``) so a comment or a substring elsewhere
    in the file cannot mimic it.
    """
    path = os.path.join(repo_dir, "databricks.yml")
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as f:
        return any(line.rstrip() == "  " + collection_key for line in f)


def _resource_files(repo_dir):
    d = os.path.join(repo_dir, "resources")
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.endswith((".yml", ".yaml")))


def read_bundle(repo_dir):
    """``(bundle_name, bundle_uuid)`` from an existing ``databricks.yml``.

    Line-scoped regex rather than a YAML parse: PyYAML is not guaranteed to be
    installed, and only the two keys under the top-level ``bundle:`` block matter.
    Returns ``(None, None)`` when there is no bundle file.
    """
    import re

    path = os.path.join(repo_dir, "databricks.yml")
    if not os.path.isfile(path):
        return None, None
    name = uuid = None
    in_bundle = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if re.match(r"^\S", line):  # a new top-level key ends the block
                in_bundle = line.startswith("bundle:")
                continue
            if not in_bundle:
                continue
            m = re.match(r"\s+name:\s*(\S+)", line)
            if m and name is None:
                name = m.group(1).strip("\"'")
            m = re.match(r"\s+uuid:\s*(\S+)", line)
            if m and uuid is None:
                uuid = m.group(1).strip("\"'")
    return name, uuid
