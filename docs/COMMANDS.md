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
cluster policy ids, CI runner. It lives outside the skill directories precisely so that
installing, re-installing or uninstalling the kit cannot destroy it.

```
$ scaffold:profile                 # report the profile in force; create it if absent
$ scaffold:profile --generate      # rewrite it, keeping every value already in it
$ scaffold:profile --show          # report only, never create
```

**One file.** `scaffold-profile.md` is what you edit and what every command reads — a
`key: value` sheet with a reference table above it saying what each field is and where to
get it. There is no apply step and no generated second copy: save the file, and the next
`/scaffold:new` uses it.

```
~/.claude/scaffold-profile.md      the profile — you edit this, new.py reads this
```

**A profile has a scope.** The values above are exactly the ones that differ between the
clients one machine serves, so the nearest project profile wins over the install-wide one:

```
$AGENT_KIT_PROFILE                     an explicit file, for one invocation
<project>/.claude/scaffold-profile.md  nearest project profile, walking up from the cwd
~/.claude/scaffold-profile.md          install-wide fallback
```

```
$ cd ~/clients/acme
$ scaffold:profile --scope project    # -> ~/clients/acme/.claude/, gitignored
$ $EDITOR ~/clients/acme/.claude/scaffold-profile.md
```

Scaffold inside `~/clients/acme` and the repo is branded from Acme's profile; scaffold
anywhere else and it falls back to the machine's. Every command that reads a profile
prints which one it used *before* it writes anything, and warns when it falls back to the
machine's while standing inside a project that has a `.claude/` of its own — that silent
case is what produces a repo branded for the wrong client.

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
> dir is unresolved, so it falls back to the repo root — and the project-scope walk is
> skipped entirely, since an uninstalled checkout has no adapter to say what a project
> directory is called. `profile.py --show` then reports a profile that is not yours. Run
> the *installed* copy under
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
  scaffold-profile.md             yours — the profile itself, read by new.py
  .agent-kit-install.json         receipt; drives uninstall

<--output-dir>/ai-<slug>-<type>/  a generated repo. Never inside .claude
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
         ✓  20 skill artifact(s)
         ✓  11 command(s)
         ✓   3 subagent(s)
         ·  guidelines render twice: canonical for the guidelines dir, plus a model-invocable copy

  [4/4]  Verifying
         ✓  31 entry points registered, zero payload
         ✓  no unresolved markers
         ✓  profile sheet untouched
         ·  receipt: .agent-kit-install.json

  ──────────────────────────────────────────────────────────────────────
  ✓  Installed  14 guidelines (10 with a conformance sheet) · 6 skills · 11 commands · 3 subagents
  ──────────────────────────────────────────────────────────────────────

    /deliver:feature
    /deliver:spec
    /diagram:build
    /diagram:review
    /eval:new
    /plan:release
    /review:mr
    /scaffold:add
    /scaffold:configure
    /scaffold:new
    /scaffold:profile
```

What the verify lines are guarding against:

| Line | Guards against |
|---|---|
| `31 entry points, zero payload` | A template `CHANGELOG` or a reference doc registering itself as a slash command. It once registered 40 commands, 22 of them payload. The count is asserted, so a payload file that starts registering itself fails the install rather than quietly appearing as a command. |
| `no unresolved markers` | Any surviving `__TOKEN__`. Scanned generally, not against a list of known names — a list is how `__ORG_PREFIX__` shipped into six installed guidelines unnoticed. |
| `profile sheet untouched` | Your filled-in profile being clobbered. Hashed before and after; a change fails the install. |

**Re-running is safe and byte-identical.** Each artifact is removed and rewritten, so a file
deleted from `core/` cannot linger as a stale command.

---

## 4. Scaffold a new repo

One repo of one type. The type picks the primary resource and what `deploy` resolves; the
GitLab pipeline, `.gitignore`, `.editorconfig`, `docs/specs/` and `CONFIG.md` come with all
six. **No standards docs** — the guidelines are read from the installed tree, never copied in.

```
$ scaffold:new --type api --slug payments --display-name "Payments API"

============================================================
  Scaffolding: ai-payments-api  (type: api)
  Output:      ~/repos/ai-payments-api
  profile: global  ~/personal/agent-kit/scaffold-profile.md
           no profile here — every value stays per-repo
============================================================
  [api] copied skeleton from templates/api-skeleton/
  [deploy] 5 files
  [gitlab] .gitlab-ci.yml
  [gitignore] kept the skeleton's own .gitignore
  [editorconfig] .editorconfig
  [specs] docs/specs/README.md
  [config] CONFIG.md — 27 placeholder(s) to fill, then {{cmd:scaffold:configure}}

  Created: ~/repos/ai-payments-api

  Next steps:
    1. CONFIG.md — fill the placeholder sheet (workspace hosts, service
       principals, developer groups, catalogs), then apply it with
       {{cmd:scaffold:configure}}.  The bundle uuid is already generated.
    2. schema/models.py — domain schemas; then implement routers/ + services/
    3. wheels/ — vendor the dependencies (see wheels/README.md) and COMMIT
       them. The Apps build environment has no network.
    4. Local dev deploy — ./run_local.sh deploy   (deploys to DEV only)
    5. Cloud deploy — set CONTROLLER_TRIGGER_TOKEN in GitLab CI/CD vars, then
       merge to the stg / prod branch. Both belong to the controller — never
       `databricks bundle deploy -t stg|prod` by hand.
    6. Scaffold the evaluation suite with {{cmd:eval:new}}
```

`[gitignore] kept the skeleton's own .gitignore` is the aspects-never-clobber rule showing
its work: `api` ships a `.gitignore` that tracks `wheels/`, so the shared one is not applied
over it. An aspect that writes nothing prints no line at all.

Every type prints the same shape. What differs:

| Type | Primary resource | Placeholders |
|---|---|---|
| `api` | Databricks App (FastAPI) | 27 |
| `etl` | Lakeflow pipeline | 19 |
| `job` | Scheduled Job, one task per stage | 17 |
| `genie` | Genie space (`genie_spaces` DAB resource) | 19 |
| `agent` | Multi-Agent Supervisor, reconciled by a deploy job | 18 |
| `fe` | Databricks App (React, prebuilt `dist/`) | 15 |

**Every type is a bundle now**, including `agent` and `genie`. That is the change worth
knowing if you used an older version: there is one deploy path — `databricks bundle deploy`
plus `bundle run` on a resource — and the controller drives stg/prod for all six. No type
carries a workspace token in CI.

An `agent` repo, whose bundle's only resource is the job that reconciles the supervisor:

```
$ scaffold:new --type agent --slug support-agent --display-name "Support Agent"

============================================================
  [agent] copied skeleton from templates/agent/
  [deploy] 7 files
  [gitlab] .gitlab-ci.yml
  [gitignore] .gitignore
  [editorconfig] .editorconfig
  [specs] docs/specs/README.md
  [config] CONFIG.md — 18 placeholder(s) to fill, then {{cmd:scaffold:configure}}

  Created: ~/repos/ai-support-agent

  Next steps:
    1. CONFIG.md — fill the placeholder sheet (workspace hosts, service
       principals, developer groups, catalogs), then apply it with
       {{cmd:scaffold:configure}}.  The bundle uuid is already generated.
    2. src/managed/agent.yml — the tools to attach, one per tool_id. A tool
       NOT declared here is deleted from the live agent.
    3. src/managed/instructions.md — routing guidance (sent byte-verbatim)
    4. ./run_local.sh plan — shows what a deploy would add, change or
       delete, before it does it
    5. Local dev deploy — ./run_local.sh deploy   (deploys to DEV only)
    6. Cloud deploy — set CONTROLLER_TRIGGER_TOKEN in GitLab CI/CD vars, then
       merge to the stg / prod branch. Both belong to the controller — never
       `databricks bundle deploy -t stg|prod` by hand.
    7. Scaffold the evaluation suite with {{cmd:eval:new}}
```

> **Why an agent's deploy is a job.** A supervisor agent has no DAB resource type — it has a
> Beta REST API (`/api/2.1/supervisor-agents`). The controller reaches project code only
> through `bundle deploy` followed by `bundle run` on a resource, so the deploy has to *be* a
> resource: `resources/deploy.job.yml` is a job that runs `python/deploy_agent.py` in the
> workspace, as the job's `run_as` principal. `run_resources.yml` lists that job, and without
> the entry a deploy uploads a new spec, changes no agent, and still reports success. Dev runs
> the same job the controller runs, so there is one deploy path rather than two.

> **Step 4 is not optional politeness.** Reconciliation deletes every live tool it does not
> find declared in `agent.yml`, and that is not recoverable from the repo. `./run_local.sh
> plan` runs the reconciler against dev with `--dry-run` and prints what would be added,
> changed or deleted. Read the delete lines before you deploy.

### Declare, don't record — how `agent` and `genie` identify what they deployed

Both deploy something a bundle cannot fully own, so both need an answer to *which* resource a
redeploy should update. **Neither stores an id** — but they get there differently now, and the
difference matters.

| | How identity is resolved | The sharp edge |
|---|---|---|
| `agent` | By **`display_name`**, looked up through the API at deploy time | Renaming `display_name` points the next deploy at a *different* agent, and creates it |
| `genie` | By the **DAB resource key** in `resources/genie.yml` | Renaming that key **destroys and recreates** the space, losing its id and every conversation in it |

For `agent`, `python/managed.py` lists, matches the name, and: one match → update; none →
create; **more than one → refuse**. Every environment is name-suffixed, prod included — one
rule with no exception, so the name is derivable from `(config, target)` alone, in CI exactly
as on a laptop.

> **Why not write the id back into the yml?** CI cannot hold it. A runner checks out fresh,
> reads an empty id, takes the create branch, and throws the write-back away when the job
> ends — one more supervisor per deploy. Per-environment id fields do not help: the id is an
> *output* of a deploy, and CI's only place to put an output is a commit, which is a race.
> Same trade a DAB target makes — declarative identity plus a per-target workspace, nothing
> about the deployment in git. Both validators reject a committed `supervisor_agent_id:` /
> `space_id:` outright, so a repo cannot drift back into storing deploy state.

`genie`'s `src/space.yml` does carry one id — the **instruction** id. That is not deploy state:
it identifies a piece of space *content* so a redeploy edits the instructions in place instead
of dropping them and adding a copy. The build mints it on first run and writes it back; commit
it with the entry it belongs to.

**CI holds no logic of its own.** Each stage runs a script that lives in the repo, so every
check that gates a deploy also runs on a laptop:

```
agent                                    genie
  python/validate.py   offline spec check  python/validate.py   offline declaration check
  python/managed.py    the reconciler      python/build_space.py  builds generated/space.<t>.json
  python/deploy_agent.py  job entry point
  run_local.sh  validate | plan | deploy   run_local.sh  build + validate, deploy to dev
```

`deploy_agent.py` calls the same `check()` that `validate.py` calls, so "valid" has one
definition rather than one per place that asks. Each validator reports *every* problem at once
rather than the first:

```
$ PYTHONPATH=python python3 python/validate.py

✗ agent.yml: tools[0] is missing description
✗ agent.yml: duplicate tool_id 'genie-registry'
✗ agent.yml: ${genie_space_id} survived substitution
```

Both types deploy through the shared DAB controller like every other bundle, and **neither
holds a workspace token in CI** — auth on stg/prod is the deploy job's `run_as` principal,
reached with `CONTROLLER_TRIGGER_TOKEN`. `agent` needs `run_resources.yml` to list its deploy
job; `genie` ships it empty, because a space is live the moment it is deployed.

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
  deploy  PRESENT  already there
  gitlab  PRESENT  already there
  api     PRESENT  already there

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
    [api] Configure logging once at startup, from settings:
          configure_logging(settings.log_level, settings.log_format, settings.service_id)
          — then remove any basicConfig / setLevel elsewhere, or LOG_LEVEL stops working.
    [api] Add the request context middleware:  app.add_middleware(RequestContextMiddleware,
          service_id=settings.service_id)  — it generates and echoes X-Request-ID and emits
          the one access-log line.
    [api] Register the exception handlers:  register_exception_handlers(app)  — this is what
          normalizes FastAPI's {'detail': ...} onto the ErrorResponse envelope and installs
          the catch-all. Then delete any per-route error bodies.
    [api] Raise from core/exceptions.py in services and repositories — never HTTPException
          below the router.
    [api] Set CORS from settings.cors_origins — an allowlist, never ['*'].

  Then:
    1. Fill CONFIG.md and apply it:   /scaffold:configure
    2. Review the added files in git before committing:  git status
```

> **The *Manual wiring* block is the honest boundary of what a file copy can do.** Copying
> `core/handlers.py` in does nothing until something calls `register_exception_handlers(app)`
> — so the script says so rather than pretending the aspect is finished.

**No standards docs are copied in, and the wiring notes cite no guideline.** Each note states
its rule — "an allowlist, never `['*']`" — rather than pointing at where the rule is written.
A section number in a comment goes stale the moment a guideline is renumbered, which is the
same failure as a copied file, so the repo carries neither. Copying the docs per repo was
measured across six repos: six different subsets, every one drifted from source, and
`/review:mr` never read them anyway — it resolves `core/guidelines/conformance/` directly.
The guidelines a repo answers to are named once, in its README.

Re-run the same add and nothing is overwritten:

```
  [api] SKIPPED routers/__init__.py — already exists (use --force to replace)
  [api] SKIPPED routers/platform.py — already exists (use --force to replace)
  [api] SKIPPED core/config.py — already exists (use --force to replace)
```

**`cicd` is two aspects now** — `deploy` (how the repo deploys: bundle descriptor,
`resources/`, `run_local.sh`, `run_resources.yml`) and `gitlab` (the pipeline and the project
setup it needs). They split because they change for different reasons: the deploy story is
per-repo-type, the CI provider is not. Asking for `cicd` prints a pointer rather than
"unknown aspect".

Adding one that is already there writes nothing and says so:

```
$ scaffold:add --repo ~/repos/ai-support-agent --aspect gitlab

==================================================================
  Repo:    ~/repos/ai-support-agent
  Type:    agent  (detected from src/managed/agent.yml)
  Adding:  gitlab
  profile: global  ~/personal/agent-kit/scaffold-profile.md
           no profile here — every value stays per-repo
==================================================================
  [gitlab] SKIPPED .gitlab-ci.yml — already exists (use --force to replace)
  [config-sheet] CONFIG.md — 18 placeholder(s) outstanding

  0 file(s) written into ~/repos/ai-support-agent
  1 left untouched (already present): .gitlab-ci.yml

  Manual wiring the copy cannot do:
    [gitlab] Run the kit's gitlab/setup-group.sh --group <id> once per group: the
             CONTROLLER_TRIGGER_TOKEN variable and the Databricks service account, both
             inherited by every project including ones added later.
    [gitlab] Run gitlab/setup-repo.sh --project <id> per repo: dev/stg/prod branches, branch
             protection, the default branch, and the controller in the job-token allowlist.
             Both scripts are a dry run until --apply.
    [gitlab] stg and prod must stay PROTECTED branches. CONTROLLER_TRIGGER_TOKEN is a
             protected variable, so an unprotected branch receives an empty one and the
             trigger posts nothing while the job still goes green.

  Then:
    1. Fill CONFIG.md and apply it:   {{cmd:scaffold:configure}}
    2. Review the added files in git before committing:  git status
```

> **The *Manual wiring* block is the honest boundary of what a file copy can do.** Copying a
> `.gitlab-ci.yml` in does nothing until the group has a trigger token and the branches exist,
> so the script says so instead of pretending the aspect is finished. The same block is where
> the protected-branch trap is recorded: an unprotected `stg` receives an empty
> `CONTROLLER_TRIGGER_TOKEN` and the trigger job still goes green.

One pipeline serves every type. It never deploys — it validates the bundle and triggers the
shared controller — so no type's CI holds a workspace token, and there is no per-type CI
variant to keep in step.

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
scaffold-profile.md
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
