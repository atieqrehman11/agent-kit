# Commands — what each one prints

Real captured output from a full lifecycle run. Paths shortened; nothing else edited.

Order below is the order you run them in: set the profile once, install, scaffold, add,
configure. Uninstall last because you will need it least.

For the shape of it rather than the output, see
[scaffold-flow](../core/skills/scaffold/docs/scaffold-flow.png) (sections 1, 4 and 5 as a
picture) and [agent-kit-overview](agent-kit-overview.png) (what installing actually does).

- [0. Nothing prompts you](#0-nothing-prompts-you)
- [1. Profile and config — the two levels of settings](#1-profile-and-config--the-two-levels-of-settings)
- [2. Where things land](#2-where-things-land)
- [3. Install](#3-install)
- [4. Scaffold a new repo](#4-scaffold-a-new-repo)
- [5. Add an aspect to a repo that already exists](#5-add-an-aspect-to-a-repo-that-already-exists)
- [6. Uninstall](#6-uninstall)
- [7. The check that runs over all of it](#7-the-check-that-runs-over-all-of-it)

---

## 0. Nothing prompts you

There is no `input()` anywhere in the installer or the scaffold scripts. They are
deterministic executors: every value arrives as a flag, and they print what they did. That is
on purpose — the same command has to run identically in your shell, in CI, and from a hook.

**The wizard is the skill, not the script.** When you type `/scaffold:new`, the model asks you
the questions — repo type, slug, catalog — and then calls `new.py` with the answers as flags.
The conversation is the interactive layer; the script is the part that has to be reproducible.

Anything the script cannot infer, it will not invent. It prints the gap instead — as
`TODO_SET_*` placeholders in `CONFIG.md`, or as a *Manual wiring* list at the end of an add.

Every command takes `--dry-run`, which prints the same output and writes nothing.

---

## 1. Profile and config — the two levels of settings

Set these before scaffolding anything. There are exactly two, and the split is about
lifetime:

| | Scope | Lives in | Set with |
|---|---|---|---|
| **Profile** | org-wide, every repo you will ever scaffold | the kit data dir (`~/.claude/`) | `/scaffold:profile` |
| **CONFIG.md** | one repo | the repo itself | `/scaffold:configure` |

The profile holds what never varies between your repos — org name, team, workspace hosts,
cluster policy ids, CI runner. It lives in the kit data dir precisely so that installing,
re-installing or uninstalling the kit cannot destroy it.

```
$ scaffold:profile --generate      # write the fill-in sheet
$ scaffold:profile                 # apply sheet -> scaffold-profile.json
$ scaffold:profile --show          # print what is saved
```

```
~/.claude/scaffold-profile.md      you fill this in (has example hints per line)
~/.claude/scaffold-profile.json    the applied values — this is what new.py reads
```

`CONFIG.md` is everything the profile could not answer for *this* repo. It is regenerated on
every scaffold and every add, keeping any value you already filled in:

```
$ scaffold:configure --repo ~/repos/legacy --generate

Wrote ~/repos/legacy/CONFIG.md
  6 placeholder(s) to fill: TODO_SET_DESCRIPTION, TODO_SET_PROD_SERVICE_PRINCIPAL,
  TODO_SET_PROD_SP_ID, TODO_SET_REPO_URL, TODO_SET_STG_SERVICE_PRINCIPAL, TODO_SET_STG_SP_ID
```

```
$ scaffold:configure --repo ~/repos/legacy --dry-run

No filled values found in the sheet (every line is blank). Nothing applied.
  6 placeholder(s) still unresolved: TODO_SET_DESCRIPTION, TODO_SET_PROD_SERVICE_PRINCIPAL,
  TODO_SET_PROD_SP_ID, TODO_SET_REPO_URL, TODO_SET_STG_SERVICE_PRINCIPAL, TODO_SET_STG_SP_ID
```

> **One footgun worth knowing.** Run these scripts from the *repo checkout* and the kit data
> dir is unresolved, so it falls back to the repo root — `profile.py --show` reports
> `(no profile saved)` even when your profile exists. Run the *installed* copy under
> `~/.claude/skills/scaffold/` and it finds it. Same reason checkout output shows a raw
> `{{cmd:…}}` token where the installed copy shows `/scaffold:configure`. **Always test
> scaffold changes against the installed copy.**

---

## 2. Where things land

Two destinations that never mix: the kit installs into `.claude`; generated repos go wherever
you point `--output-dir`.

```
~/.claude/                        install target — and the kit data dir
  guidelines/                     14 canonical copies + 3 conformance sheets
  skills/       commands/         registered entry points
  agents/                         critic, reviewer, qa
  scaffold-profile.md             yours — the fill-in sheet
  scaffold-profile.json           yours — applied values, read by new.py
  .agent-kit-install.json         receipt; drives uninstall

<--output-dir>/ai-<slug>-<type>/  a generated repo. Never inside .claude
  docs/*_STANDARDS.md             copied from core/guidelines at scaffold time
  docs/*_CONFORMANCE.md           the audit sheet beside each standard
  docs/specs/README.md            the per-feature spec convention /deliver:* reads and writes
  docs/specs/<feature>/           requirements · design · tasks · report, one folder per feature
  CONFIG.md                       this repo's TODO_SET_* sheet
```

`guidelines/`, `skills/`, `commands/` and `agents/` are **replaced wholesale** on every
install. Everything else in the target is left alone — which is what makes it safe for the kit
to install into the same directory that holds your own state.

### Repo folder naming

The folder is `<prefix>-<slug>-<type>`, and each part is added **only where the slug does not
already say it**. Matching is on whole hyphen-delimited tokens, wherever they appear — so
`api-gateway` is not turned into `ai-api-gateway-api`, while `rapid` still gets its suffix
because its "api" is three letters of a word, not the type.

| `--slug` | `--type` | folder |
|---|---|---|
| `payments` | `api` | `ai-payments-api` |
| `sales-api` | `api` | `ai-sales-api` |
| `api-gateway` | `api` | `ai-api-gateway` |
| `rapid` | `api` | `ai-rapid-api` |
| `support-agent` | `agent` | `ai-support-agent` |
| `kb` | `genie` | `ai-kb-genie` |

Two ways to control it:

| | |
|---|---|
| **`repo_prefix`** in the profile | Changes the prefix for every repo you scaffold. Defaults to `ai`. Set it to your own (`confiz`, `ua-ai`) or leave it **blank for no prefix at all** — `payments` + `api` then gives `payments-api`. |
| **`--repo-name`** on one command | Replaces the whole folder name, prefix, slug, type and all. `--slug billing --repo-name totally-custom-name` creates `totally-custom-name/`. |

---

## 3. Install

Four phases. Phase 2 is the one that matters: **nothing is written until validation passes**,
so a malformed artifact cannot half-install.

```
$ python3 adapters/claude/install.py ~/.claude

  agent-kit → Claude
  ──────────────────────────────────────────────────────────────────────
  source     ~/personal/agent-kit
  target     ~/.claude

  [1/4]  Checking prerequisites
         ✓  python 3.9.6 · target writable

  [2/4]  Validating core/ (nothing is written until this passes)
         ✓  22 artifacts, frontmatter valid
         ✓  every command reference resolves

  [3/4]  Rendering
         ✓  14 guideline(s)
         ✓  19 skill artifact(s)
         ✓  10 command(s)
         ✓   3 subagent(s)
         ·  guidelines render twice: canonical for the guidelines dir, plus a model-invocable copy

  [4/4]  Verifying
         ✓  29 entry points registered, zero payload
         ✓  no unresolved markers
         ✓  profile sheet untouched
         ·  receipt: .agent-kit-install.json

  ──────────────────────────────────────────────────────────────────────
  ✓  Installed  14 guidelines (3 with a conformance sheet) · 5 skills · 10 commands · 3 subagents
  ──────────────────────────────────────────────────────────────────────

    /deliver:feature
    /deliver:spec
    /diagram:build
    /diagram:review
    /eval:new
    /plan:release
    /scaffold:add
    /scaffold:configure
    /scaffold:new
    /scaffold:profile
```

What the verify lines are guarding against:

| Line | Guards against |
|---|---|
| `29 entry points, zero payload` | A template `CHANGELOG` or a reference doc registering itself as a slash command. It once registered 40 commands, 22 of them payload. |
| `no unresolved markers` | Any surviving `__TOKEN__`. Scanned generally, not against a list of known names — a list is how `__ORG_PREFIX__` shipped into six installed guidelines unnoticed. |
| `profile sheet untouched` | Your filled-in profile being clobbered. Hashed before and after; a change fails the install. |

**Re-running is safe and byte-identical.** Each artifact is removed and rewritten, so a file
deleted from `core/` cannot linger as a stale command.

---

## 4. Scaffold a new repo

One repo of one type. The type picks the primary resource and the CI/CD wiring; the standards
docs, `.gitignore` and `CONFIG.md` come with all five.

```
$ scaffold:new --type api --slug payments --display-name "Payments API"

============================================================
  Scaffolding: ai-payments-api  (type: api)
  Output:      ~/repos/ai-payments-api
============================================================
  [api] copied skeleton from templates/api-skeleton/
  [cicd] .gitlab-ci.yml, team_config.yaml, .bundleignore, run_resources.yml
  [standards] 5 files
  [gitignore] .gitignore
  [config] CONFIG.md — 15 placeholder(s) to fill, then /scaffold:configure

  Created: ~/repos/ai-payments-api

  Next steps:
    1. CONFIG.md           — fill the placeholder sheet (hosts, service principals,
                             policy ids, team, repo url), then apply it with:
                             /scaffold:configure   (uuid is already generated)
    2. schema/models.py    — domain schemas; implement routers/ + services/
    3. Local dev deploy    — ./bundle.sh   (deploys to DEV only)
    4. Cloud deploy        — set CONTROLLER_TRIGGER_TOKEN in GitLab CI/CD vars,
                             then merge to the stg / prod branch
```

Every type prints the same shape with its own aspects and next steps. What differs:

| Type | Primary resource | Docs it receives | Placeholders |
|---|---|---|---|
| `api` | Databricks App (FastAPI) | API + PYTHON + SERVICE_STRUCTURE (+2 conformance) | 15 |
| `etl` | Lakeflow pipeline | PIPELINE + PYTHON | 11 |
| `job` | Scheduled Job | JOB + PYTHON + SERVICE_STRUCTURE (+1 conformance) | 11 |
| `genie` | Genie space (Genie management API) | GENIE + PYTHON | 4 |
| `agent` | Multi-Agent Supervisor (`supervisor_agents` API) | AGENT + PYTHON | 2 |

> **Only `api` and `job` get the service-structure standard.** A Genie space is configuration,
> and an agent is instructions plus a tool list handed to a managed supervisor service —
> neither has a request boundary of its own, so shipping them a layering standard would be
> noise.

An `agent` repo, which has no bundle — its two placeholders are the CI image and runner:

```
$ scaffold:new --type agent --slug support-agent --display-name "Support Agent"

============================================================
  Scaffolding: ai-support-agent  (type: agent)
  Output:      ~/repos/ai-support-agent
============================================================
  [agent] copied skeleton from templates/agent/
  [standards] docs/AGENT_STANDARDS.md, docs/PYTHON_STANDARDS.md
  [gitignore] .gitignore
  [specs] docs/specs/README.md
  [config] CONFIG.md — 2 placeholder(s) to fill, then /scaffold:configure

  Created: ~/repos/ai-support-agent

  Next steps:
    1. supervisor/instructions.md — write the supervisor's routing instructions
    2. supervisor/supervisor.yml  — set display_name/description + the tools list
                                    (each tool: id, type, description + its id)
    3. Local dev deploy           — ./deploy.sh   (reconciles '<name> [DEV]',
                                    attaches tools, prints the working URL)
    4. Cloud deploy               — set DATABRICKS_HOST + DATABRICKS_TOKEN in
                                    GitLab CI/CD vars per branch, then merge to
                                    the stg / prod branch
    5. Scaffold evaluation with /eval:new
```

> **An agent repo does not just carry instructions — it provisions the supervisor.** `api`,
> `etl` and `job` deploy through a Databricks Asset Bundle; `agent` and `genie` have no bundle
> resource, so they call a management API from a deploy script instead. For `agent` that means
> `deploy.sh` runs `src/deploy.py`, which reads `supervisor/supervisor.yml` + `instructions.md`
> and reconciles the supervisor through the workspace's `supervisor_agents` SDK service, then
> `create_tool` for each entry in the `tools:` list. It is the scripted equivalent of building
> the supervisor in the Agents tab, and it prints the same working query URL the UI would give
> you. `supervisor_agents` is Preview, so `deploy.py` imports the tool classes lazily and fails
> with a named error if your `databricks-sdk` predates the service; only `knowledge_assistant`
> and `genie_space` tool types are wired, and any other `type:` raises with the supported list
> and a pointer at `_build_tool`.

### Declare, don't record — how the non-bundle types identify what they deployed

`agent` and `genie` deploy real resources without a bundle, so they need their own answer to
*which* resource a redeploy should update. Both give the same one.

**Neither repo stores an id.** `supervisor.yml` and `space.yml` declare what should exist;
they do not record what does. Identity is two axes together:

| Axis | Source |
|---|---|
| Which workspace | `DATABRICKS_HOST` / the CLI profile the deploy authenticated with |
| Which resource in it | the name `"<display_name\|title> [ENV]"`, from config + `--env` |

The deploy script lists, matches that name, and: one match → update; none → create;
**more than one → refuse**. Every environment is suffixed, prod included — one rule, no
exception, so the name is derivable from `(config, env)` alone in CI as on a laptop.

> **Why not write the id back into the yml?** CI cannot hold it. A runner checks out fresh,
> reads an empty id, takes the create branch, and throws the write-back away when the job
> ends — one more supervisor (or Genie space) per deploy. Per-environment id fields do not
> help: the id is an *output* of a deploy, and CI's only place to put an output is a commit,
> which is a race. Same trade a DAB target makes — declarative identity plus a per-target
> workspace, nothing about the deployment in git.

The sharp edge: **the name is the identity.** Renaming `display_name` or `title` does not
rename the deployed resource — the next deploy creates a new one. Both validate scripts also
reject a `supervisor_agent_id:` / `space_id:` key outright, so a repo cannot drift back to
storing deploy state.

Both repos are laid out identically, and **CI holds no logic of its own** — each stage is one
line that runs a script in the repo:

```
src/validate.py    check the declaration — no credentials, no network, no SDK
src/deploy.py      reconcile the resource   (--env dev|stg|prod)
deploy.sh          local one-shot: pip install + deploy.py (dev)
.gitlab-ci.yml     validate: python src/validate.py
                   deploy:   python src/deploy.py --env "$CI_COMMIT_BRANCH"
```

That split is the point of the rename from `deploy_genie.py` / an inline CI heredoc: every
check that gates a deploy is runnable on a laptop before you push, and `deploy.py` calls the
same `validate.check()` before it touches a workspace — so "valid" has one definition instead
of one per place that asks. `validate.py` reports *every* problem at once rather than the
first, so one run tells you everything to fix:

```
$ python src/validate.py

ERROR: supervisor/supervisor.yml: instructions_file 'nope.md' does not resolve to a file
ERROR: supervisor/supervisor.yml: remove 'supervisor_agent_id'. Deploy state does not belong
       in the repo — the supervisor is resolved by name (docs/AGENT_STANDARDS.md §3a)
ERROR: supervisor/supervisor.yml: tools[0] is missing description
```

The deploy stage is manual-gated on `stg` and `prod`. Neither type uses the DAB controller, so
neither gets `team_config.yaml` or `run_resources.yml`; what they need instead is
`DATABRICKS_HOST` + `DATABRICKS_TOKEN` set per branch, which is what actually separates the
environments.

---

## 5. Add an aspect to a repo that already exists

The same slices `new` composes, applied one at a time — including to repos the scaffold never
created. Start by asking what is missing.

```
$ scaffold:add --repo ~/repos/ai-payments-api --detect

==================================================================
  Repo:    ~/repos/ai-payments-api
  Type:    api  (detected from resources/api.app.yml)
  Bundle:  payments_api   uuid 08a8a83a-c0dc-497c-b856-703551ae5cd3
==================================================================
  cicd  PRESENT  already there
  api   PRESENT  already there

  Standard set complete for an api repo.
```

Pointed at a plain FastAPI repo with nothing but an `app.py`, the type is inferred from
`databricks.yml` and the whole service spine goes in:

```
$ scaffold:add --repo ~/repos/legacy --aspect api

==================================================================
  Repo:    ~/repos/legacy
  Type:    api  (detected from databricks.yml resources.apps)
  Adding:  api
==================================================================
  [api] added routers/__init__.py
  [api] added routers/platform.py
  [api] added core/__init__.py
  [api] added core/config.py
  [api] added core/logging_setup.py
  [api] added core/exceptions.py
  [api] added core/handlers.py
  [api] added core/middleware.py
  [api] added schema/__init__.py
  [api] added schema/models.py
  [api] added services/__init__.py
  [api] added repositories/__init__.py
  [standards] added docs/API_STANDARDS.md   (always included)
  [standards] added docs/PYTHON_STANDARDS.md   (always included)
  [standards] added docs/API_STANDARDS_CONFORMANCE.md   (always included)
  [standards] added docs/SERVICE_STRUCTURE_STANDARDS.md   (always included)
  [standards] added docs/SERVICE_STRUCTURE_STANDARDS_CONFORMANCE.md   (always included)
  [gitignore] added .gitignore   (always included)
  [specs] added docs/specs/README.md   (always included)
  [config-sheet] CONFIG.md — 1 placeholder(s) outstanding

  19 file(s) written into ~/repos/legacy

  Manual wiring the copy cannot do:
    [api] Wire the router into your FastAPI app:  from routers import platform  →
          app.include_router(platform.router)
    [api] Check core/config.py — service_id / display_name / description feed GET /v1/info. If
          the repo already had its own config module, merge into Settings and delete the other
          one; two config modules means two answers to the same question.
    [api] Configure logging once at startup, from settings:  configure_logging(...)  — then
          remove any basicConfig / setLevel elsewhere, or LOG_LEVEL stops working.
    [api] Add the request context middleware — it generates and echoes X-Request-ID and emits
          the one access-log line (docs/API_STANDARDS.md §10).
    [api] Register the exception handlers — this is what normalizes FastAPI's {'detail': ...}
          onto the ErrorResponse envelope and installs the catch-all (docs/API_STANDARDS.md §7).
    [api] Raise from core/exceptions.py in services and repositories — never HTTPException
          below the router (docs/SERVICE_STRUCTURE_STANDARDS.md §3).
    [api] Set CORS from settings.cors_origins — an allowlist, never ['*'].

  Then:
    1. Fill CONFIG.md and apply it:   /scaffold:configure
    2. Review the added files in git before committing:  git status
```

> **The *Manual wiring* block is the honest boundary of what a file copy can do.** Copying
> `core/handlers.py` in does nothing until something calls `register_exception_handlers(app)`
> — so the script says so rather than pretending the aspect is finished.

The `[standards]` lines are there because the code the aspect delivers *cites* those docs.
Without them, adding the api aspect produced a repo with no `docs/` and ten pointers into
nothing.

Re-run the same add and nothing is overwritten:

```
  [api] SKIPPED routers/__init__.py — already exists (use --force to replace)
  [api] SKIPPED routers/platform.py — already exists (use --force to replace)
  [api] SKIPPED core/config.py — already exists (use --force to replace)
```

The `cicd` aspect, and what it flags when a bundle uuid is missing:

```
$ scaffold:add --repo ~/repos/legacy --aspect cicd

  [cicd] added .gitlab-ci.yml
  [cicd] added team_config.yaml
  [cicd] added .bundleignore
  [cicd] added run_resources.yml
  [config-sheet] CONFIG.md — 6 placeholder(s) outstanding

  4 file(s) written into ~/repos/legacy

  Heads-up:
    ! No bundle uuid found — generated 9bce6c94-376b-42ca-8fa4-5ba42bfed471. Put the SAME uuid
      in databricks.yml (bundle.uuid); the controller identifies the bundle by it, and it must
      never change after the first deploy.

  Manual wiring the copy cannot do:
    [cicd] Set CONTROLLER_TRIGGER_TOKEN in GitLab > Settings > CI/CD > Variables (masked)
           before the first stg/prod deploy.
    [cicd] Confirm BUNDLE_TAG in .gitlab-ci.yml matches bundle.name in databricks.yml, and that
           team_config.yaml's bundle_name + uuid match it too.
    [cicd] Push the `stg` / `prod` branches — the pipeline fires on merge to each.
```

On a `genie` or `agent` repo the same aspect installs a different pipeline — and the scripts
that pipeline calls. Here, a hand-built agent repo that only ever had a `supervisor/` folder:

```
$ scaffold:add --repo ~/repos/legacy-agent --aspect cicd

==================================================================
  Repo:    ~/repos/legacy-agent
  Type:    agent  (detected from supervisor/supervisor.yml)
  Adding:  cicd
==================================================================
  [cicd] added .gitlab-ci.yml
  [cicd] added src/validate.py
  [cicd] added src/deploy.py
  [standards] added docs/AGENT_STANDARDS.md   (always included)
  [standards] added docs/PYTHON_STANDARDS.md   (always included)
  [gitignore] added .gitignore   (always included)
  [specs] added docs/specs/README.md   (always included)
  [config-sheet] CONFIG.md — 2 placeholder(s) outstanding
```

> **The pipeline brings the scripts it invokes.** Its two jobs are `python src/validate.py`
> and `python src/deploy.py`, so shipping the `.gitlab-ci.yml` alone would install a pipeline
> pointing at files that are not there — the same broken-pointer class the `[standards]` lines
> exist to prevent. On a scaffolded repo that already has them, both are reported `SKIPPED`.

Everything available:

```
$ scaffold:add --list

Aspects  (--aspect KEY, repeatable; 'all' = the standard set, minus what
          the repo already has)

  cicd  CI/CD pipeline
        GitLab pipeline that deploys this repo to stg/prod — bundle types via the shared DAB
        controller (+ the per-environment config a job reads); genie/agent validate their
        declaration, then run their own deploy script with --env <branch>
        types: api, etl, job, genie, agent

  api   Use case API surface
        GET /v1/health and GET /v1/info, plus the service spine they need: validated settings,
        one logging setup, one exception hierarchy behind one handler layer, and request-id
        middleware
        types: api

Always included with any add, wherever missing — never asked about:
  docs/         the standards for this repo type, each with its conformance sheet
  .gitignore    the shared Python / Databricks ignore file
  docs/specs/   the per-feature spec convention /deliver:spec reads and writes
  CONFIG.md     regenerated, keeping any value already filled in

An existing file is never overwritten — it is reported as SKIPPED (--force replaces).
```

---

## 6. Uninstall

Driven by the receipt, not by re-scanning `core/` — so an artifact deleted from the source
since you installed is still removed, and a file you added by hand is still left alone.

```
$ python3 adapters/claude/install.py ~/.claude --uninstall --dry-run

  agent-kit → Claude
  ──────────────────────────────────────────────────────────────────────
  source     ~/personal/agent-kit
  target     ~/.claude  (dry run)

  [1/1]  Uninstalling
         ✓  47 artifact(s) removed (dry run)
         ·  kit data dir kept: ~/.claude

  ──────────────────────────────────────────────────────────────────────
  ✓  Uninstalled
```

47 = 14 guidelines + 3 conformance sheets + 19 skill dirs + 9 commands + 2 agents. Drop
`--dry-run` and the output is identical minus the marker. What is left afterwards:

```
$ ls -A ~/.claude

my-notes.md
scaffold-profile.json
```

Both were placed there before the uninstall. Directories the install created are removed only
once empty; **the kit data dir itself is never removed**, so your profile survives.

---

## 7. The check that runs over all of it

Every claim above is a test. Each is written as a property — it makes the failure happen and
asserts the tool refuses — rather than matching a string already known to be there.

```
$ bash adapters/claude/conformance.sh

== §2.4 verification (per install) ==
  PASS  install exits 0 on a clean target
  PASS  declared entry points == registered
  PASS  zero surviving markers
  PASS  every rendered /skill:verb reference resolves to an installed command
  PASS  kit data dir contents byte-identical after install (obligation 11)
  PASS  every installed .py parses
  PASS  receipt written, lists all four kinds + source + timestamp
  PASS  every registered entry point carries a description (§1.5)
  PASS  rendered frontmatter parses as YAML with string-typed values
  PASS  conformance siblings installed as payload, none registered (§1.2)
  PASS  a conformance sibling with no guideline fails the install
  PASS  an undeclared __TOKEN__ fails the install (general scan, not a denylist)
  PASS  installed tree contains no unresolved __TOKEN__ of any name

== §2.5 conformance (the adapter itself) ==
  PASS  installing twice produces an identical tree
  PASS  artifact deleted from core/ disappears from the install
  PASS  uninstall removes exactly the receipt contents; data dir survives
  PASS  leak test: no core/ file names Claude's paths, filenames or invocation syntax
  PASS  adapter README states which kinds are supported and how each is expressed
  PASS  obligations 1-10 implemented and annotated

  20 passed, 0 failed
```
