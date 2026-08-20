# scaffold

A four-command skill for standing up **Databricks repos** — and
keeping their config out of your way. You scaffold a repo of one type, and every
machine- and repo-specific value is either baked in from a shared profile or left as a
`TODO_SET_*` placeholder you fill in one pass later.

![scaffold workflow](docs/scaffold-flow.png)

Source: [`docs/scaffold-flow.drawio`](docs/scaffold-flow.drawio). It lives here rather than
in the repo's top-level `docs/` so it cannot drift from the skill it describes — and, being
documentation rather than payload, it is never installed (STANDARD.md §1.3). Edit the
`.drawio` and re-render the PNG; a stale diagram is worse than none.

| Command | What it does | Direction |
|---|---|---|
| [`{{cmd:scaffold:profile}}`](commands/profile.md) | Set up the org/project values shared by every repo (branding, team, CI/CD, cluster policies) — once per scope. | `scaffold-profile.md` |
| [`{{cmd:scaffold:new}}`](commands/new.md) | Scaffold a new repo (type-driven wizard: `api` · `etl` · `job` · `fe` · `agent` · `genie`). | templates → new repo |
| [`{{cmd:scaffold:add}}`](commands/add.md) | Add **one aspect** — the `deploy` config, the `gitlab` pipeline, or the `api` surface — to a repo that already exists. | templates → existing repo |
| [`{{cmd:scaffold:configure}}`](commands/configure.md) | Fill the per-repo `TODO_SET_*` placeholders a scaffolded repo ships with. | `CONFIG.md` → repo |

## The two-level config model

The whole design exists to answer one question for every setting: *is this the same for
every repo my team makes, or genuinely specific to this one?*

- **Profile** (`{{cmd:scaffold:profile}}`) — the constants: org/branding, workspace project
  folder, team & ownership, CI/CD controller, cluster policies. Collected **once** and
  baked into every repo you scaffold thereafter.
- **`CONFIG.md`** (`{{cmd:scaffold:configure}}`) — the per-repo values: workspace hosts, service
  principals, repo URL, catalog, table prefix. Each scaffolded repo ships a one-page
  `CONFIG.md` listing exactly the placeholders it still contains.

Anything you leave blank in the profile simply stays a per-repo `TODO_SET_*` placeholder,
so the split is a soft default, not a hard boundary.

## Typical flow

```
# once per scope — the machine, or one client's tree
{{cmd:scaffold:profile}}                      # creates + reports it; add --scope project
edit <the file it reports>                    # fill shared values — no apply step

# per use case
{{cmd:scaffold:new}}                          # interactive wizard → creates the repo
edit <repo>/CONFIG.md                  # fill the per-repo placeholders
{{cmd:scaffold:configure}}                    # apply them across the repo tree

# for a repo that already exists (including one this tool never made)
{{cmd:scaffold:add}}                          # pick an aspect → deploy, gitlab, or api
{{cmd:scaffold:configure}}                    # apply the placeholders the new files brought in
```

## Repo types

`{{cmd:scaffold:new}}` produces one repo of a **single type**, chosen by *what the repo produces*,
not the tech inside it:

| Type | Primary resource | Deploy | CI/CD |
|---|---|---|---|
| `api` | `resources.apps` — FastAPI Databricks App | `bundle deploy` + `run` | shared controller |
| `etl` | `resources.pipelines` — Lakeflow declarative pipeline | `bundle deploy` | shared controller |
| `job` | `resources.jobs` — scheduled Databricks Job | `bundle deploy` | shared controller |
| `fe` | `resources.apps` — React Databricks App | `bundle deploy` + `run` | shared controller |
| `genie` | `resources.genie_spaces` — Genie space | `bundle deploy` | shared controller |
| `agent` | Agent Bricks Multi-Agent Supervisor | `bundle deploy` + `run` | shared controller |

**One deploy path, for every type.** No repo deploys itself and none holds a workspace token
in CI. The controller reaches project code only through `bundle deploy` and `bundle run`, so
a repo running its own deploy script would be a second, ungoverned path into the same
workspaces.

What differs between types is the **payload**, not the mechanism:

- `fe` ships a committed `dist/` — the Apps build environment cannot resolve
  `registry.npmjs.org`, so nothing can be built there.
- `genie` ships a committed `generated/space.<target>.json` — the controller clones fresh
  and runs no project scripts, so the artifact is built locally. The catalog is baked in per
  target, because DAB reads a `file_path` payload verbatim rather than resolving `${var.*}`
  inside it.
- `agent` has no DAB resource type at all, so the bundle's one resource is a **job whose
  single task runs the reconciler**. `run_resources.yml` lists it, and that `bundle run`
  *is* the deploy.

`genie` and `agent` store no id: DAB owns the Genie space's identity through its resource
key, and the agent is resolved by `display_name` in the target workspace.

### `fe` — the one repo that is not Python

Everything else in this skill assumes a Python repo, and `fe` is the exception the registry
had to learn. Three places encode it, all of them one-liners:

- **`GUIDELINE_NAMES`** — `fe` maps to `react` alone, with no `python` entry, so its README
  points at the one guideline its code can actually be held to. Naming a repo a standard
  nobody in it can act on is worse than naming none.
- **its own `.gitignore`** — the shared one is Python-flavoured, and `fe`'s ignores
  `node_modules/`, `dist/`, `.vite/`. `dist/` stays uncommitted in both, but for opposite
  reasons: build junk there, the deployed payload here.
- **an inverted `.bundleignore`** — the shared one excludes `dist/`. `fe`'s excludes `src/`
  and `node_modules/` and *keeps* `dist/`, because the deployed app is `dist/` +
  `server.mjs` + `app.yml` and nothing else. That is only possible because `server.mjs` has
  no dependencies — Node built-ins only, so nothing is installed at app startup and a cold
  start cannot fail on the npm registry. Add a runtime dependency there and the trade
  changes.

`server.mjs` is also where two rules from the `react` guideline are actually enforced rather
than asserted: the browser only ever calls a same-origin `/api` path (so no backend host or
token reaches `dist/`), and the process **exits at startup** when required configuration is
missing, rather than booting and 500-ing on first use.

## Aspects — the same pieces, à la carte

A repo is not monolithic: it is a type skeleton plus a few **aspects**. Each aspect is one
named slice, defined once in [`aspects.py`](aspects.py) and applied through one function, so
*"the deploy aspect"* means the identical set of files whether it lands in a brand-new repo or a
five-year-old one. Two are choosable:

| Aspect | Adds | Types |
|---|---|---|
| `deploy` | How the repo deploys: `databricks.yml` + `resources/` + `run_local.sh` + `run_resources.yml` (+ `.bundleignore` where it applies). Every type gets a bundle descriptor; the descriptor and resource it resolves differ per type. `fe` also gets the sync block that keeps `package.json` out of the app root; `genie` gets `python/build_space.py`; `agent` gets the reconciler under `python/`. | `api` `etl` `job` `fe` `genie` `agent` |
| `gitlab` | The GitLab pipeline: `.gitlab-ci.yml` — validate the bundle, then trigger the shared DAB controller on merge to `stg`/`prod`. One pipeline for every type, and none of them holds a workspace token. The GitLab project setup it needs is `gitlab/setup-group.sh` (once per group) and `gitlab/setup-repo.sh` (per repo) — kit tooling, not repo files. | `api` `etl` `job` `fe` `genie` `agent` |
| `api` | `routers/platform.py` (`GET /v1/health` + `GET /v1/info`) plus the service spine those endpoints need: `core/` (validated settings, one logging setup, one exception hierarchy behind one handler layer, request-id middleware), `schema/`, `services/`, `repositories/` | `api` |

The rest are **not decisions**, so they are never offered: `.gitignore` (the Node one on an
`fe` repo, one that tracks `wheels/` on an `api` repo, the shared Python / Databricks one
everywhere else), `.editorconfig`, `docs/specs/README.md`, and a regenerated `CONFIG.md` come
with **any** add wherever they are missing. They live in the same
registry — one definition each — just flagged `selectable: False`, and `add --list` prints
them straight from `AUTO` so the list cannot drift from what a run actually applies.

`docs/specs/` is seeded with a README and nothing else. A convention needs somewhere to land
before the first feature or the first spec gets written wherever that run happened to guess —
but a placeholder example folder is the kind of thing people copy rather than replace, so
there isn't one. {{cmd:deliver:spec}} and {{cmd:deliver:feature}} create the per-feature
folders.

## Standards are not a repo file

There is no `standards` aspect, and no `docs/*_STANDARDS.md`. The guidelines live in
`core/guidelines/` and install to `~/.claude/guidelines/`. A scaffolded repo's own README
names the ones that govern it; nothing else in the repo points at them.

It used to copy them in. Measured across six repos built from this scaffold: six *different*
subsets of the docs, and every copy drifted from source — 25 to 106 differing lines, with
`PYTHON_STANDARDS.md` identically stale in all three repos that had it. The copy was a
snapshot of whichever commit each repo was scaffolded from, and `review` never read it anyway:
the reviewer resolves `core/guidelines/conformance/<name>.md` directly. A stale rule that
looks authoritative is worse than no rule in the repo at all.

**Template code cites nothing — not even a guideline name.** The first attempt kept the
citations and only changed their form, so `docs/API_STANDARDS.md §7` became `api guideline §7`.
That is the same bug one level down: a section number goes stale the moment a guideline is
renumbered, and there were about forty of them. Each comment now states its rule instead —
`# An allowlist from configuration. Never ["*"].` The rule is the part a reader needs at the
callsite; the reasoning is what the guideline is for.

`GUIDELINE_NAMES` maps a repo type to its guideline names, for the README pointer only. It
carries names, never paths into a repo, so adding a guideline does not add a file to anything.

Per-environment config is deliberately *inside* `deploy` rather than beside it: the
dev/stg/prod split exists because the controller deploys per target, so it is part of the
deploy story, not a separate thing to choose. Every type expresses it the same way — bundle
variables in `databricks.yml`, overridden per target. `api` and `fe` turn them into the App's
env through the `config:` block of their app resource; `job` passes them to each task as
`base_parameters`; `genie` bakes them into the built artifact.

There is no `config/{DEV,STG,PROD}/task_config.yaml`. A per-environment config file makes the
values a run used invisible: you end up reading a file in the workspace and inferring which
one the run picked up, and a `config_dir` pointing at the wrong target does not surface until
the output is wrong. Explicit parameters show up on the task's own run page.

`{{cmd:scaffold:new}}` applies each type's **standard set** (`DEFAULT_BY_TYPE`); `{{cmd:scaffold:add}}`
applies a single aspect to an existing repo, and `--aspect all` restores exactly that standard
set. An aspect valid for a type but outside its standard set (`api` in an already-scaffolded
api repo) stays opt-in by name.

Adding an aspect is **one entry in `ASPECTS`** — both commands pick it up, and
`add.py --detect` reports its status against any repo with no further wiring.

### Writing into a repo you did not create

`{{cmd:scaffold:add}}` is the only command that touches an existing repo, so it is deliberately
narrow: it writes **only the files the chosen aspect owns** (no tree-wide token substitution),
it **skips and reports** any file that already exists (`--force` replaces it and keeps a
`.bak`), `--dry-run` writes nothing, and `--detect` tells you the repo's type, its bundle
identity, and what is missing before anything is written. Steps a file copy cannot perform —
editing the repo's own `databricks.yml` or `app.py` — are printed as **manual wiring** rather
than left implied.

## Files

```
scaffold/
  SKILL.md                           model-invoked entry point
  commands/                          user-invoked entry points, one per verb
    profile.md  new.md  add.md  configure.md
  profile.py  new.py  add.py  configure.py    the script behind each verb
  aspects.py                         aspect registry (files / types / wiring) + repo-type detection
  config_tokens.py                   TODO_SET_* token registry (group / label / example)
  templates/                         PAYLOAD — one dir per type
    api-skeleton/  etl-bundle/  job-bundle/  fe/  agent/  genie/
    deploy/  gitlab/  common/        deploy config, GitLab pipeline, shared fragments
  README.md                          DOCUMENTATION — this file. Never installed
  docs/                              DOCUMENTATION — the workflow diagram. Never installed
```

The standards a scaffolded repo receives are **not** copied into `templates/`: they are read
straight from `core/guidelines/` at scaffold time, so there is one source of truth rather
than a second copy drifting from the first.

Every file a scaffolded repo ships with lives under `templates/` as a **real file** with
`TPLVAR_*` / `TODO_SET_*` tokens — the Python is pure orchestration. `new.py` scaffolds
every type through one path (`copytree(templates/<type>/)` + token substitution) driven by
a small table, so **adding a type is a new `templates/<type>/` dir plus one row in the map.**

## How a token gets resolved

At scaffold time each token is resolved in order, and the first match wins:

1. an explicit `new.py` CLI arg,
2. the **profile** (`scaffold-profile.md`, org-wide values) — the project's own if the
   working directory sits under one, else the install-wide one,
3. otherwise a `TODO_SET_*` placeholder left for `{{cmd:scaffold:configure}}`.

To extend the system:

- **New profile field** → add a row to `FIELDS` in `profile.py`, then map its key to a
  template token in `new.py` (`_PROFILE_TODO_TOKENS`, or a `TPLVAR_` assignment for inline
  tokens).
- **New per-repo placeholder** → register it in `config_tokens.py` (token → group, label,
  example) so it groups correctly in generated `CONFIG.md` sheets. Unregistered tokens still
  appear under an "Other" group, so nothing is silently missed.
- **New aspect** → one entry in `ASPECTS` in `aspects.py` (files/dirs it owns, which types it
  applies to, `selectable`, any manual wiring), plus its key in `ORDER` and — if new repos
  should get it — in `DEFAULT_BY_TYPE`. `{{cmd:scaffold:new}}`, `{{cmd:scaffold:add}}` and `add.py --detect`
  all pick it up with no further changes. Keep the choosable set small: anything a user should
  never have to think about belongs in `AUTO` or in a type's skeleton, not in a picker.

## Where repos land

`{{cmd:scaffold:new}}` creates the repo in **`$SCAFFOLD_OUTPUT_DIR`**, the profile's `output_dir`,
or the current directory if both are unset (override per-run with `--output-dir`):

```bash
export SCAFFOLD_OUTPUT_DIR="$HOME/repos"     # or set output_dir in the profile sheet
```

Resolution order: `--output-dir` > `$SCAFFOLD_OUTPUT_DIR` > profile `output_dir` > CWD.
The repo is created at `<output-dir>/<repo-name>/` (default `ai-<slug>-<type>`).

---

See the top-level [README](../../../README.md) for install instructions, and each command's own
`.md` for the detailed flow.
