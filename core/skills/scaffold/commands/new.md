---
name: new
kind: command
description: >
  Create a new Databricks repo of a single type — ETL bundle, job bundle, API skeleton,
  React front end, agent or Genie space — with CI/CD wired for that type. Use when starting
  a repo from nothing.
arguments: "[repo type and name; prompted if omitted]"
---

# Scaffold a new Databricks repo (type-driven wizard)

Creates one repo of a **single type**. The type selects the primary resource; CI/CD is
wired for every type.

| Type | Primary resource | Deploy mechanism | CI/CD |
|---|---|---|---|
| `api` | `resources.apps` — FastAPI Databricks App | `bundle deploy` + `run` | shared controller |
| `etl` | `resources.pipelines` — Lakeflow declarative pipeline | `bundle deploy` | shared controller |
| `job` | `resources.jobs` — scheduled Databricks Job | `bundle deploy` | shared controller |
| `fe` | `resources.apps` — React (Vite + TS) Databricks App | `bundle deploy` + `run`, after a build | shared controller |
| `genie` | `resources.genie_spaces` — Genie space | `bundle deploy` | shared controller |
| `agent` | Agent Bricks Multi-Agent Supervisor | `bundle deploy` + `run` | shared controller |

> `apps` / `jobs` / `pipelines` / `genie_spaces` are the DAB **schema collection keys**
> (always plural, even for one resource). The single resource key under them is singular and
> derived from the slug.

**Deployment model — one path, for every type:**
- **dev** is the LOCAL dev loop: `./run_local.sh deploy`, this laptop → dev workspace, dev
  only. **stg/prod** are CLOUD deploys the shared CI/CD controller runs on merge to the
  `stg`/`prod` branch. Never run `bundle deploy -t stg|prod` locally.
- No type deploys itself, and no repo holds a `DATABRICKS_TOKEN` in CI. The controller
  reaches project code only through `bundle deploy` and `bundle run`, so a repo running its
  own deploy script would be a second path into the same workspaces that nobody governs.

What differs between the types is the **payload**:
- **`fe`** ships a committed `dist/`. The Apps build environment cannot resolve
  `registry.npmjs.org`, so nothing can be built there or in CI.
- **`genie`** ships a committed `generated/space.<target>.json`, built from `src/` by
  `python/build_space.py`. The controller clones fresh and runs no project scripts, so the
  artifact has to be in git — and the catalog is baked in per target, because DAB resolves
  `${var.*}` inside an inline `serialized_space` but reads a `file_path` payload verbatim.
- **`agent`** has no DAB resource type, so the bundle's one resource is a **job whose single
  task runs the reconciler** against `/api/2.1/supervisor-agents`. `run_resources.yml` lists
  it, and that `bundle run` *is* the deploy. Omit the entry and the deploy uploads a new spec,
  changes no agent, and reports success.

> **Neither `genie` nor `agent` stores deploy state.** DAB owns the Genie space's identity
> through its resource key in `resources/genie.yml` — renaming that key destroys and
> recreates the space, losing every conversation in it. The agent is resolved by
> `display_name`, set per target, so renaming it points the next deploy at a *different*
> agent. See the `agent` guideline §3a / the `genie` guideline.

## Choosing the type

The type is decided by **what the repo produces**, not by the tech inside it. Apply this
in order and stop at the first match:

| If the deliverable is… | Type | Resource |
|---|---|---|
| An HTTP service / interactive backend | `api` | `resources.apps` |
| A **browser UI** — dashboard, console, chat surface | `fe` | `resources.apps` |
| A set of **Delta tables** built by declarative transforms (ingest → bronze → silver → gold, with data quality) | `etl` | `resources.pipelines` |
| An **action run on a schedule** — export, orchestration/glue, batch scoring, maintenance, or triggering a pipeline | `job` | `resources.jobs` |
| A conversational / tool-routing **supervisor agent** given instructions + a list of tools | `agent` | Agent Bricks Multi-Agent Supervisor |
| **Natural-language-to-SQL** over curated tables | `genie` | `resources.genie_spaces` |

### `api` + `fe` — two repos, one product

A product with a UI is **two repos**, not one: `api` for the backend, `fe` for the browser.
Scaffold both. They are separately deployable Databricks Apps, and the split is what lets the
front end proxy rather than expose — the browser calls the `fe`'s **same-origin** `/api` path,
`server.mjs` forwards it to the `api` App, and the backend's URL and the token used to reach
it never enter the shipped bundle.

Scaffold the `api` first: `fe`'s `TODO_SET_BACKEND_API_URL` is the api App's URL, and the api
repo's app resource grants the front end's service principal `CAN_USE`. If the user asks for
"a dashboard", ask whether the backend exists yet — if it does not, that is two scaffolds, and
say so before running either.

### `etl` vs `job` — the one ambiguous pair

Both can run on a schedule, so cadence does **not** decide it. They are **complementary, not
generational** — `etl` is a declarative *transformation engine*; `job` is a general
*orchestrator / runner*. The sharp test:

> **Does the repo materialize/maintain a graph of Delta tables via declarative transforms?**
> **Yes → `etl`.** **No — it performs an *action* (export, orchestrate, score, maintain,
> trigger) → `job`.**

- "bronze → silver → gold, Auto Loader ingestion, `@dp.table`, expectations" → **`etl`** (the
  preferred way to build tables; declarative is recommended for transformation work).
- "nightly export the gold table / call an API / batch-score a model / compact tables" →
  **`job`** (a pipeline *cannot* do these — it only defines tables).
- A `job` is **not** "old-school ETL." Its reason to exist is the non-transformation work
  above. If you only need to transform tables, use `etl`, not a job-with-notebook.
- **They often coexist**: a pipeline does not schedule itself — a `job` can trigger it
  (`pipeline_task`) and do the export afterward. When you need both, scaffold the **`etl`**
  repo first; add a `job` later only for the surrounding orchestration.

## Wizard

Run this **entirely as an interactive wizard using the `AskUserQuestion` tool**. This
applies to **every type** (`api`/`etl`/`job`/`fe`/`agent`/`genie`) and to **every field** — do
**not** drop to plain inline text prompts at any step. `AskUserQuestion` is a multiple-choice
picker; free-text values (slug, names, description, URLs, etc.) are captured via the **"Other"**
option on each question, which lets the user type. Every question needs **at least two
options** (the tool rejects fewer); the **"Other"** free-text choice is added automatically,
so for a pure free-text field give two example/suggestion options and let the user pick "Other"
to type their own. Batch related questions into a single
`AskUserQuestion` screen (up to four questions per screen) so the user answers a compact form,
not a chain of one-at-a-time prompts. If `{{args}}` already supplies a value, skip that
question. At the end, echo the full resolved config and get a confirm before running anything.

**Keep startup minimal.** Collect exactly four fields on one screen — `type`, `slug`,
`repo-name`, `description`. The **display name is auto-derived** from the slug (Title Case,
e.g. `payments` → `Payments`); do not spend a question on it (the author can rename it in the
generated `spec.py`/docstring later). Everything else (workspace, catalog, table prefix,
team) is written as a `TODO_SET_` placeholder that `{{cmd:scaffold:configure}}` resolves in one
pass from the generated `CONFIG.md`. **Do not** ask a separate "which optional inputs to set
now?" screen — that work is deferred to `configure` by design.

**Step 1 — One form (AskUserQuestion, one screen, four questions).** Ask **Type**, **Slug**,
**Repo name**, and **Description** together on a single screen:

- **Type** (single-select) — six types exist but the picker shows at most four buttons plus
  the auto-added **"Other"**, so present `api` · `fe` · `etl` · `genie` as buttons and **name
  the other two explicitly in the question text** (*"Not buttons — choose 'Other' and type the
  name: `job` (a scheduled action: export / orchestrate / batch-score / maintain / trigger a
  pipeline), `agent` (a tool-routing supervisor)."*). Never bury `genie` or `fe` in Other —
  both are easy to forget exist, which is exactly when a wrong type gets picked. Use
  **Choosing the type** above to guide the user; if they are unsure between `etl` and `job`,
  apply the "materialize tables vs perform an action" test and state which the answer implies
  before confirming. If they pick `fe`, ask whether the backend `api` repo already exists —
  a UI with no backend is two scaffolds, not one.
- **Slug** — kebab-case identifier. It is a **free-text field**, so the two placeholder
  options are illustrative examples ONLY — label them clearly ("example only — choose Other to
  type your real slug") and use neutral values that do **not** collide with existing repo
  slugs (e.g. `network-anomaly`, `signal-quality`), never a real existing repo slug.
- **Repo name** — free text; the two placeholder options are the computed default
  **`ai-<slug>-<type>`** and a shorter **`<slug>-<type>`** variant, plus "Other"
  to type any name. Do not hardcode the prefix; accept whatever the user types. (`<slug>` may
  not be known when you author the options — use the example slug in the labels and treat the
  user's typed value as authoritative; if they pick a templated label, substitute the real
  slug before running.)
- **Description** — one sentence (free text via "Other"; if the user picks a non-text option,
  ask them for the sentence before running rather than proceeding on the button label).

The **display name is not asked** — derive it from the slug (Title Case). That is the *only*
input screen; everything else is deferred to `{{cmd:scaffold:configure}}`.

**Step 2 — Confirm (AskUserQuestion, one screen).** Echo the full resolved config (type, slug,
repo name, derived display name, description) and ask a single **Proceed / Cancel** confirm.
On confirm, run the scaffold.

Optional (sensible defaults; only ask to override): `--gitlab-runner` (`devops-ci-new`),
`--controller-project-id` (`77857303`), `--data-sensitivity` (`pii`).

## Run

After confirming, run the scaffold script with the resolved values. Pass only `--type`,
`--slug`, `--display-name`, `--description` (and `--repo-name` if the user overrode the
default). In the streamlined flow you **always omit** `--workspace-url`, `--catalog`,
`--table-prefix`, `--team-name`, and `--team-email` — each becomes a `TODO_SET_` placeholder
that `{{cmd:scaffold:configure}}` fills later from `CONFIG.md` (do not pass them at all, and do
not type the placeholder yourself):

```bash
python3 __SKILL_DIR__/new.py \
  --type <api|etl|job|fe|genie|agent> \
  --slug "<slug>" \
  --display-name "<display name>" \
  --description "<one sentence>" \
  [--repo-name "<repo-name>"] \        # default: ai-<slug>-<type>
  [--output-dir "<dir>"] \             # default: $SCAFFOLD_OUTPUT_DIR, else profile output_dir, else CWD
  [--workspace-url "<dev-workspace-url>"] \
  [--catalog "<catalog>"] \
  [--table-prefix "<prefix>"] \
  [--team-name "<team>"] [--team-email "<email>"]
```

The repo is created at `<output-dir>/<repo-name>/` (default `ai-<slug>-<type>`;
`<output-dir>` is `--output-dir`, else `$SCAFFOLD_OUTPUT_DIR`, else the profile's
`output_dir`, else the current directory).
Bundle types get a fresh lowercase bundle `uuid`; the script prints a per-type next-steps
checklist.

## After scaffolding

- Report the full path of the created repo and the printed next-steps.
- **Standards are not copied into the repo.** The guidelines live in agent-kit and install to
  `~/.claude/guidelines/<name>.md`; the repo's code cites them by name (`api guideline §7`) and
  its `README.md` names the ones that govern it — `python` plus the per-type guideline, or
  `react` alone for an **`fe`** repo, which is TypeScript end to end, `server.mjs` included.
  Point the user at `~/.claude/guidelines/`, and say that without agent-kit installed they do
  not have the standards.
- **Placeholders** — every deferred input is written as a `TODO_SET_` token (e.g.
  `TODO_SET_DEV_WORKSPACE_HOST`, `TODO_SET_CATALOG`, `TODO_SET_TABLE_PREFIX`,
  `TODO_SET_TEAM_NAME`) and listed in the repo's generated `CONFIG.md`. Tell the user to fill
  `CONFIG.md` and run **`{{cmd:scaffold:configure}}`** to apply them in one pass, and name which
  tokens are outstanding.
- **api** — domain schemas live in `schema/models.py`; runtime `command`/`env` live in
  `app.yml` (single source of truth — the app resource in `resources/api.app.yml` no longer
  duplicates them).
- **Controller types (`api`/`etl`/`job`)** — remind the user to fill the `TODO_SET_*` values
  in `databricks.yml` (stg/prod hosts, service principals, policy ids) before the first
  cloud deploy. Registration with the platform team is a **prerequisite**, not something
  the scaffold produces: the bundle name + uuid must already be in the team registry and
  the stg/prod service principals already created, or the controller's governance stage
  rejects the deploy. GitLab setup is `gitlab/setup-group.sh` then `gitlab/setup-repo.sh`. Local dev testing: `./run_local.sh deploy`.
- **api** also: set `TODO_SET_WAREHOUSE_ID` / `TODO_SET_CHAT_GATEWAY_URL` in `app.yml`
  (the runtime env), and register the domain with the shared chat gateway service
  (its `domain_configs/`).
- **fe** — `npm run setup` first: it installs dependencies **and** vendors the shadcn/ui
  components into `src/shared/ui/` (they are vendored, not a dependency, which is why that
  folder is excluded from lint and format). Then `npm run dev`. A feature is **one entry in
  `src/app/registry.ts`** — nav and routes are both derived from it, so adding a page edits
  no shell file, and `src/app/registry.test.tsx` asserts that. Set
  `TODO_SET_BACKEND_API_URL` in `app.yml` to the `api` App's URL; the browser only ever
  calls the same-origin `/api` path and `server.mjs` proxies it, so no backend host or token
  reaches `dist/`. The proxy authenticates as **the app's own service principal** by default
  (`BACKEND_API_AUTH=sp` — Databricks Apps injects the client id + secret, nothing to store),
  so the one thing to get right is granting that principal `CAN_USE` on the `api` App:
  `TODO_SET_FRONTEND_SP_ID` in the api repo's app resource. Forwarding the signed-in user's
  token instead (`obo`) is implemented and commented ready in `resources/fe.app.yml` — tell
  the user it is the intended direction, but only once the backend authorizes per user. Cloud deploy goes through the DAB controller like the other bundle
  types, so it needs `CONTROLLER_TRIGGER_TOKEN` (group-level) — not a workspace token. What
  differs is the payload: `dist/` is **committed**, because the Apps build environment cannot
  resolve `registry.npmjs.org` and the controller deploys from a fresh clone. Tell the user
  to rebuild and commit `dist/` whenever `src/` changes — a stale one deploys green and
  serves the previous bundle — and that `pnpm run verify` is what `./run_local.sh deploy` runs. Full guidance: the `react` guideline.
- **agent** — write the routing guidance in `src/managed/instructions.md`, then set the
  `tools` list in `src/managed/agent.yml` (each: `tool_id`, `tool_type`, the type-specific
  spec, and a `description` that says when to route there *and what it does not cover*).
  `./run_local.sh` validates offline; `./run_local.sh plan` shows what a deploy would add,
  change or **delete**; `./run_local.sh deploy` does it against dev. Tell the user two
  things: a tool NOT declared in `agent.yml` is deleted from the live agent, including
  anything added in the Agents-tab UI — so run `plan` before touching the tool list; and
  every `${name}` must be set per target in `databricks.yml`, because a Genie space id is
  workspace-local and the dev value is never valid in stg. Agent Bricks is Preview — confirm
  the tool-type names first. Full guidance: the `agent` guideline.
- **genie** — no dummy content is scaffolded: `src/views/` and `src/functions/` ship empty,
  and `data_sources.yml` / `sql_functions.yml` / `example_queries.yml` ship with empty lists
  and a worked example in comments. Point `src/data_sources.yml` at curated gold tables you
  already own, write `src/instructions.md`, then fill `src/example_queries.yml` — the
  question→SQL few-shot pairs are the biggest accuracy lever a space has. Tell the user
  three things: every identifier must start with `${catalog}.${schema}.` or a stg deploy
  silently reads dev (`python/validate.py` enforces it); `./run_local.sh all` must be run and
  `generated/` committed before promoting, or stg deploys a stale space; and the DDL under
  `src/{views,functions}/` is **not** deployed by the bundle — apply it to the catalog
  yourself, or the space deploys clean and answers nothing. Full walkthrough:
  the `genie` guideline.
- To score the deployed stack, scaffold `evaluation/` with `{{cmd:eval:new}}`.
- To add a **single piece** later — or to a repo this command never created — use
  **`{{cmd:scaffold:add}}`**: the `deploy` config, the `gitlab` pipeline, or the `api` surface (`/v1/health` +
  `/v1/info`). It restores what a repo of that type would have had, without touching anything
  else in the repo.

## Example

Every step is an `AskUserQuestion` picker — no inline text prompts:

```
{{cmd:scaffold:new}}
→ [picker] Type / Slug / Repo / Desc?   etl |                       (ONE screen, 4 questions;
   (api·fe·etl·genie are buttons;         signal-quality |           free text via "Other";
    job and agent named in the            ai-signal-quality-etl |
    Type question → Other)                Monitors cable signal health…
   (display name auto-derived: Signal Quality)
→ [picker] Confirm?                      Proceed / Cancel
✓ Confirm → runs new.py --type etl --slug signal-quality --display-name "Signal Quality" \
              --repo-name ai-signal-quality-etl --description "…"
   (workspace/catalog/table-prefix/team NOT passed → TODO_SET_ placeholders in CONFIG.md;
    fill CONFIG.md, then {{cmd:scaffold:configure}})
```
