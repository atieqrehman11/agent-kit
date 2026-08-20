"""Composable repo **aspects** — the slices a repo is made of, one at a time.

An *aspect* is a named, self-contained piece of a scaffolded repo: its CI/CD
pipeline, its deploy descriptor, the platform endpoints every API must expose.
Standards are not among them — the guidelines live in agent-kit and are read from
there, never copied in. ``new.py`` applies several when it creates a repo from
scratch; ``add.py`` applies one to a repo that **already exists**. Both go
through :func:`apply` here, so "the deploy aspect" means exactly the same set of
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


def _src_path(src_rel):
    """Resolve a files-tuple source against the template tree."""
    return os.path.join(TEMPLATES, src_rel)


# Repo types, mirrored from new.py (kept here so add.py needs only this module).
# Bundle types deploy with `databricks bundle deploy`, and all of them hand
# stg/prod to the shared DAB CI/CD controller. `fe` differs only in payload: it
# ships a committed dist/ rather than source, because the Apps build environment
# cannot reach the npm registry.
BUNDLE_TYPES = ("api", "etl", "job", "fe")
CONTROLLER_TYPES = ("api", "etl", "job", "fe")
API_TYPES = ("genie", "agent")
ALL_TYPES = BUNDLE_TYPES + API_TYPES

# Which guidelines govern each repo type. Names only — they resolve to
# core/guidelines/<name>.md in agent-kit and are never copied into a repo. Used to
# print the pointer a scaffolded README carries, so that a citation in template
# code ("api §7") names something the reader can go and find.
#
# `fe` gets no `python` entry: it is TypeScript end to end, server.mjs included.
GUIDELINE_NAMES = {
    "api": ("api", "service-structure", "python"),
    "etl": ("pipeline", "python"),
    "job": ("job", "service-structure", "python"),
    "fe": ("react",),
    "agent": ("agent", "python"),
    "genie": ("genie", "python"),
}

# Tool caches a formatter/linter may have dropped in a template dir.
_IGNORE = {"__pycache__", ".ruff_cache", ".pytest_cache", ".DS_Store"}


def run_resources_yaml(vars_) -> str:
    """``run_resources.yml`` — resource keys the controller runs after deploy.

    Deployment only registers a definition; execution is separate. Which of the
    two a repo needs is a per-type fact, not a preference:

    * ``api`` / ``fe`` — deploy uploads the source, but it is ``bundle run`` that
      creates the app deployment making it live. Without the key the previous
      version keeps serving, and the deploy still reports success.
    * ``agent`` — the bundle's only resource IS the deploy job, so without the key
      nothing reconciles the agent at all.
    * ``job`` / ``etl`` / ``genie`` — empty. A job runs on its schedule, and a
      Genie space is live the moment it is deployed. Forcing a run here would
      re-execute the pipeline on every merge.

    ``vars_["TPLVAR_RUN_RESOURCE_KEY"]`` carries the key when the type needs one.
    """
    header = (
        "# Resource keys the controller runs (`bundle run`) after a successful\n"
        "# deploy. Deployment only registers a definition — execution is separate.\n"
    )
    key = (vars_ or {}).get("TPLVAR_RUN_RESOURCE_KEY", "")
    if key:
        return (
            f"{header}#\n"
            "# The key must match the resource key in resources/, NOT the resource's\n"
            "# `name:` — they are different strings and only the first one resolves.\n"
            f"resources:\n  - {key}\n"
        )
    return (
        f"{header}#\n"
        "# Deliberately EMPTY: nothing here has to run for the deploy to be complete.\n"
        "# A job runs on its schedule or a manual trigger; a Genie space is live as\n"
        "# soon as it is deployed. Listing a key would re-run the work on every merge.\n"
        "resources: []\n"
    )


# ─── The registry ─────────────────────────────────────────────────────────────

# Wiring notes are *manual* steps: things a file copy provably cannot do, such as
# editing a databricks.yml or an app.py the repo already owns. They are printed
# after an apply and are the honest boundary of what the script did.
# Wiring notes are *manual* steps: things a file copy provably cannot do, such as
# editing a databricks.yml the repo already owns. They are printed after an apply
# and are the honest boundary of what the script did.

# ── deploy aspect ────────────────────────────────────────────────────────────
_DEPLOY_WIRING = [
    "Registration is a prerequisite, not an output: the platform team must already "
    "hold this bundle_name + uuid in the team registry, and must have created the "
    "stg/prod service principals. Confirm bundle.name and bundle.uuid here match "
    "what was registered, and that BUNDLE_TAG in the pipeline matches too — a "
    "mismatch fails the controller's governance stage, not your own pipeline.",
    "Set run_as on stg and prod to the registered service principal ids. The "
    "controller reads them out of databricks.yml and fails governance without them.",
    "`./run_local.sh` runs the repo locally; `./run_local.sh deploy` deploys to dev. "
    "stg and prod are the controller's — never `bundle deploy -t stg|prod` by hand.",
]

_FE_DEPLOY_WIRING = [
    "Commit dist/. `./run_local.sh deploy` builds it; the controller deploys from a "
    "fresh clone, so an uncommitted dist/ fails validate_bundle with "
    "`stat dist: no such file or directory`.",
    "Rebuild and commit dist/ whenever src/ changes. Nothing enforces this — a stale "
    "dist/ deploys green and serves the previous bundle.",
    "Keep package.json out of the app root (the sync block in databricks.yml). If it "
    "reaches the workspace the platform attempts an install, which fails with "
    "`EAI_AGAIN registry.npmjs.org`.",
]

_GENIE_DEPLOY_WIRING = [
    "Commit generated/space.<target>.json. `./run_local.sh all` builds every "
    "environment; the controller deploys from a fresh clone and runs no project "
    "scripts, so an unbuilt or stale artifact deploys green and serves the previous "
    "space.",
    "Delete any `space_id:`/`genie_space_id:` left in src/space.yml, and any "
    "deploy_genie.py the repo used to carry. DAB owns the space's identity through "
    "the resource key in resources/genie.yml — a committed id is deploy state, and "
    "python/validate.py rejects it.",
    "The views and functions under src/ are NOT deployed by the bundle: DAB has no "
    "resource for arbitrary SQL. Apply src/{views,functions}/*.sql to the catalog "
    "yourself, or the space deploys clean and answers nothing.",
]

_AGENT_DEPLOY_WIRING = [
    "The bundle's only resource is a JOB that runs the reconciler — a supervisor "
    "agent has no DAB resource type, and the controller reaches project code only "
    "through `bundle run`. That is why run_resources.yml lists deploy_agent: without "
    "it the deploy uploads the spec and changes no agent.",
    "Delete any `supervisor_agent_id:` left in the spec, and any deploy.sh the repo "
    "used to carry. The agent is resolved by display_name, so a committed id is "
    "deploy state the repo must not hold.",
    "Every ${name} in src/managed/agent.yml must be passed as a --var by "
    "resources/deploy.job.yml and declared as a variable in databricks.yml. An "
    "unresolved one fails the deploy rather than reaching the API — but only "
    "because deploy_agent.py checks for it.",
]

# ── gitlab aspect ────────────────────────────────────────────────────────────
# The setup scripts are kit tooling, not repo files: they configure the GitLab
# PROJECT, so shipping them into every repo would be N copies of one procedure.
_GITLAB_WIRING = [
    "Run the kit's gitlab/setup-group.sh --group <id> once per group: the "
    "CONTROLLER_TRIGGER_TOKEN variable and the Databricks service account, both "
    "inherited by every project including ones added later.",
    "Run gitlab/setup-repo.sh --project <id> per repo: dev/stg/prod branches, branch "
    "protection, the default branch, and the controller in the job-token allowlist. "
    "Both scripts are a dry run until --apply.",
    "stg and prod must stay PROTECTED branches. CONTROLLER_TRIGGER_TOKEN is a "
    "protected variable, so an unprotected branch receives an empty one and the "
    "trigger posts nothing while the job still goes green.",
]

_JOB_DEPLOY_WIRING = [
    "The tasks are serverless notebook tasks taking explicit base_parameters — no "
    "job cluster, no policy_id, no per-environment config file. Every value a stage "
    "reads is visible in the run itself. If you genuinely need a classic cluster "
    "(custom runtime, init script, unresolvable library), resources/job.job.yml "
    "carries the job_clusters block to paste in, and you must then set policy_id per "
    "target — the run-as principal cannot create a cluster without one.",
    "config_dir and policy_id are declared in databricks.yml but unused. Leave them: "
    "the controller passes both on every deploy and `bundle deploy` errors on an "
    "undeclared --var.",
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
    "it generates and echoes X-Request-ID and emits the one access-log line.",
    "Register the exception handlers:  register_exception_handlers(app)  — this is what "
    "normalizes FastAPI's {'detail': ...} onto the ErrorResponse envelope and installs the "
    "catch-all. Then delete any per-route error bodies.",
    "Raise from core/exceptions.py in services and repositories — never HTTPException "
    "below the router.",
    "Set CORS from settings.cors_origins — an allowlist, never ['*'].",
]

ASPECTS = {
    # ── The two aspects a user picks ─────────────────────────────────────────
    "deploy": {
        "label": "Deploy config",
        "summary": (
            "How this repo deploys, independent of CI provider: bundle descriptor, "
            "resource definitions, the run_local.sh entrypoint, and the registry entry "
            "the DAB controller reads"
        ),
        "applies_to": ALL_TYPES,
        "selectable": True,
        "files": {
            "api": [
                ("deploy/bundleignore", ".bundleignore"),
                ("deploy/api/databricks.yml", "databricks.yml"),
                # No app.yml at the source root: it uploads verbatim and cannot
                # hold a per-environment value, so every target would get dev's
                # warehouse. command/env live in resources/api.app.yml under
                # `config:`, which goes through DAB variable resolution.
                ("deploy/api/run_local.sh", "run_local.sh"),
            ],
            "etl": [
                ("deploy/bundleignore", ".bundleignore"),
                ("deploy/etl/databricks.yml", "databricks.yml"),
                ("deploy/etl/run_local.sh", "run_local.sh"),
            ],
            "job": [
                ("deploy/bundleignore", ".bundleignore"),
                ("deploy/job/databricks.yml", "databricks.yml"),
                ("deploy/job/run_local.sh", "run_local.sh"),
            ],
            # fe ships a prebuilt dist/ rather than source: the Apps build
            # environment cannot resolve registry.npmjs.org, so nothing installs
            # or builds there. See deploy/fe/databricks.yml.
            "fe": [
                ("deploy/fe/databricks.yml", "databricks.yml"),
                ("deploy/fe/run_local.sh", "run_local.sh"),
            ],
            # A genie_spaces resource (CLI 1.3.0+, engine: direct). The space
            # CONTENT is a committed artifact under generated/, built from src/ —
            # DAB resolves ${var.*} inside an inline serialized_space but reads a
            # file_path target verbatim, so the catalog is baked in per target.
            "genie": [
                ("deploy/genie/databricks.yml", "databricks.yml"),
                ("deploy/genie/run_local.sh", "run_local.sh"),
                ("deploy/genie/python/build_space.py", "python/build_space.py"),
                ("deploy/genie/python/validate.py", "python/validate.py"),
            ],
            # A supervisor agent has no DAB resource type, so the bundle's one
            # resource is a job whose single task runs the reconciler. That is
            # what makes it deployable by the controller at all.
            "agent": [
                ("deploy/agent/databricks.yml", "databricks.yml"),
                ("deploy/agent/run_local.sh", "run_local.sh"),
                ("deploy/agent/python/deploy_agent.py", "python/deploy_agent.py"),
                ("deploy/agent/python/managed.py", "python/managed.py"),
                ("deploy/agent/python/validate.py", "python/validate.py"),
            ],
        },
        "dirs": {
            "api": [("deploy/api/resources", "resources")],
            "etl": [("deploy/etl/resources", "resources")],
            "job": [("deploy/job/resources", "resources")],
            "fe": [("deploy/fe/resources", "resources")],
            "genie": [("deploy/genie/resources", "resources")],
            "agent": [("deploy/agent/resources", "resources")],
            "*": [],
        },
        # run_resources.yml tells the CONTROLLER what to run after deploy. Every
        # type has one now, because every type goes through the controller.
        "generated": {"*": [("run_resources.yml", run_resources_yaml)]},
        "wiring": {
            "*": _DEPLOY_WIRING,
            "job": _DEPLOY_WIRING + _JOB_DEPLOY_WIRING,
            "fe": _DEPLOY_WIRING + _FE_DEPLOY_WIRING,
            "genie": _DEPLOY_WIRING + _GENIE_DEPLOY_WIRING,
            "agent": _DEPLOY_WIRING + _AGENT_DEPLOY_WIRING,
        },
    },
    "gitlab": {
        "label": "GitLab CI/CD",
        "summary": (
            "The GitLab pipeline and the project setup it needs — validate the bundle, "
            "then trigger the shared DAB controller on merge to stg/prod. One pipeline "
            "for every type; none of them holds a workspace token"
        ),
        "applies_to": ALL_TYPES,
        "selectable": True,
        "files": {"*": [("gitlab/gitlab-ci.controller.yml", ".gitlab-ci.yml")]},
        "dirs": {"*": []},
        "generated": {"*": []},
        "wiring": {"*": _GITLAB_WIRING},
    },
    "api": {
        "label": "Use case API surface",
        "summary": (
            "GET /v1/health and GET /v1/info, plus the service spine those "
            "endpoints need: validated settings, one logging setup, one exception "
            "hierarchy behind one handler layer, and request-id middleware"
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
    # `gitignore` / `editorconfig` / `specs` / `config-sheet` are applied
    # automatically wherever they are missing. They are in the registry so there is
    # still one definition of each, but they never appear in a picker — nobody
    # should have to decide about them.
    #
    # There is no `standards` aspect. The guidelines live in agent-kit and are read
    # from there; a copy in each repo was six different subsets across six repos,
    # every one of them drifted from the source, and the reviewer never read them
    # anyway — it resolves core/guidelines/ directly. See README.md §Standards.
    # Not style policing. Two files in these repos are sent byte-verbatim to a
    # platform API and compared byte for byte on the next deploy, so an editor
    # that adds a trailing newline turns a no-op deploy into a content change.
    # The rule has to live somewhere the editor reads, which is this file.
    "editorconfig": {
        "label": ".editorconfig",
        "summary": (
            "line endings, indent width, and the two prose files that must NOT be "
            "trailing-newline-normalised (Genie instructions, an agent's prompt)"
        ),
        "applies_to": ALL_TYPES,
        "selectable": False,
        "files": [("common/editorconfig", ".editorconfig")],
    },
    "gitignore": {
        "label": "Python / Databricks .gitignore",
        "summary": "the shared .gitignore (venvs, .databricks/, build + deploy artifacts)",
        "applies_to": ALL_TYPES,
        "selectable": False,
        # fe gets a Node one. The shared file ignores dist/ as build junk, which
        # is right everywhere except here, where dist/ is the deployed payload —
        # still not committed, but for a different reason, and the file says so.
        # fe gets a Node one, and api gets one that TRACKS wheels/ — the shared
        # file used to ignore it while databricks.yml relied on `sync: include:
        # wheels/**`, which uploads the deploying laptop's wheels and leaves the
        # controller's fresh clone with none.
        "files": {
            "*": [("common/gitignore", ".gitignore")],
            "fe": [("fe/.gitignore", ".gitignore")],
            "api": [("api-skeleton/.gitignore", ".gitignore")],
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
ORDER = [
    "deploy",
    "gitlab",
    "api",
    "gitignore",
    "editorconfig",
    "specs",
    "config-sheet",
]

# What a user chooses between. Everything else in ASPECTS is applied for them.
SELECTABLE = [k for k in ORDER if ASPECTS[k].get("selectable")]

# Applied automatically by `add` after the chosen aspects, wherever missing — no
# question asked, no menu entry. Order matters: config-sheet last.
# The code these aspects ship states its rules plainly and cites nothing — a section
# number in a comment goes stale the moment a guideline is renumbered. The README
# pointer each template carries is the one place that names the guidelines.
AUTO = ["gitignore", "editorconfig", "specs", "config-sheet"]

# Keys that are not choices, mapped to where that work lives now — so anyone who
# reaches for one gets a pointer instead of "unknown aspect".
MERGED = {
    "env-config": (
        "job tasks take explicit base_parameters now, not a per-target config file. "
        "See resources/job.job.yml."
    ),
    "api-platform": "it is now called `api`.",
    "standards": (
        "the guidelines are not copied into a repo any more. They live in agent-kit "
        "(core/guidelines/) and are read from there; each README names the ones that "
        "govern the repo."
    ),
    "gitignore": ".gitignore is applied automatically wherever it is missing.",
    "editorconfig": ".editorconfig is applied automatically wherever it is missing.",
    "specs": "docs/specs/README.md is applied automatically wherever it is missing.",
    "config-sheet": "CONFIG.md is regenerated automatically after every add.",
}

# The **standard set** per type: what a repo of this type gets from `new`, and so
# what `add --aspect all` restores in a repo that predates the scaffold.
#
# It is the same set for every type now, because every type deploys the same way.
# What varies is inside the aspects — `deploy` resolves a different descriptor and
# a different resource per type — not which aspects a type gets.
#
#   deploy       bundle descriptor + resources/ + run_local.sh + run_resources.yml
#   gitlab       the controller pipeline, and the project setup it needs
#   gitignore    shared, except api (tracks wheels/) and fe (Node, tracks dist/)
#   editorconfig the byte-verbatim prose rules
#   specs        docs/specs/README.md
#
# `api` (the use case API surface) is NOT here: it ships inside the api-skeleton
# template already. The aspect exists for FastAPI repos the scaffold never made.
# README.md likewise ships inside each template dir (tokens patched by _patch_tree).
_STANDARD_SET = ("deploy", "gitlab", "gitignore", "editorconfig", "specs")
DEFAULT_BY_TYPE = {t: _STANDARD_SET for t in ALL_TYPES}


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

    # genie and agent are checked FIRST, and by their payload rather than their
    # resource file. Both are bundles now: an agent repo's only resource is
    # resources/deploy.job.yml, which the .job.yml scan below would read as a
    # plain `job` repo.
    if os.path.isfile(j("src", "space.yml")) or os.path.isfile(
        j("genie-space", "space.yml")  # pre-bundle layout
    ):
        return "genie", "src/space.yml"
    if os.path.isfile(j("src", "managed", "agent.yml")) or os.path.isfile(
        j("supervisor", "supervisor.yml")  # pre-bundle layout
    ):
        return "agent", "src/managed/agent.yml"
    if _resource_files(repo_dir) == ["genie.yml"]:
        return "genie", "resources/genie.yml"

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
