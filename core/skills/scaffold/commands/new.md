# Scaffold a new Databricks repo (type-driven wizard)

Creates one repo of a **single type**. The type selects the primary resource; CI/CD is
wired for every type.

| Type | Primary resource | Deploy mechanism | CI/CD |
|---|---|---|---|
| `api` | `resources.apps` — FastAPI Databricks App | `bundle deploy` | enterprise controller |
| `etl` | `resources.pipelines` — Lakeflow declarative pipeline | `bundle deploy` | enterprise controller |
| `job` | `resources.jobs` — scheduled Databricks Job | `bundle deploy` | enterprise controller |
| `agent` | Agent Bricks Multi-Agent Supervisor | `supervisor_agents` SDK (`./deploy.sh`) | script (CI/CD deferred) |
| `genie` | Genie space | Genie management API (`createspace`/`updatespace`) | validate → apply DDL → deploy script |

> `apps` / `jobs` / `pipelines` are the DAB **schema collection keys** (always plural, even
> for one resource). The single resource key under them is singular and derived from the slug.

**Deployment model:**
- **Bundle types (`api`/`etl`/`job`)** — **dev** is the LOCAL dev loop (`./bundle.sh`,
  this laptop → dev workspace, dev only); **stg/prod** are CLOUD deploys the shared CI/CD
  controller runs on merge to the `stg`/`prod` branch. Never run `bundle deploy -t stg|prod`
  locally.
- **`agent`** — no DAB bundle. A **Multi-Agent Supervisor** created via the Databricks
  `supervisor_agents` SDK — the scripted equivalent of the Agents-tab UI. `supervisor/`
  holds the definition (`supervisor.yml`: display_name, description, tools list +
  `instructions.md`), and `src/deploy.py` creates/updates the supervisor, attaches the
  listed tools, and prints the working query URL. **local**: `./deploy.sh`; CI/CD is
  deferred. (Agent Bricks + the `supervisor_agents` SDK are Public Preview — confirm the
  service/tool-type names first.)
- **`genie`** — no DAB bundle. `genie-space/space.yml` is the definition and points to
  `description.md` + `instructions.md` (long prose kept out of the YAML); `deploy_genie.py`
  assembles the `serialized_space` payload and calls the Genie management API. **local**:
  `./deploy.sh`; **stg/prod**: CI runs the deploy script on branch merge. (Genie management
  API is Public Preview — confirm the `w.genie.*` calls before first deploy.)

## Choosing the type

The type is decided by **what the repo produces**, not by the tech inside it. Apply this
in order and stop at the first match:

| If the deliverable is… | Type | Resource |
|---|---|---|
| An HTTP service / interactive backend | `api` | `resources.apps` |
| A set of **Delta tables** built by declarative transforms (ingest → bronze → silver → gold, with data quality) | `etl` | `resources.pipelines` |
| An **action run on a schedule** — export, orchestration/glue, batch scoring, maintenance, or triggering a pipeline | `job` | `resources.jobs` |
| A conversational / tool-routing **supervisor agent** given instructions + a list of tools | `agent` | Agent Bricks Multi-Agent Supervisor (SDK) |
| **Natural-language-to-SQL** over curated tables | `genie` | Genie management API |

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
applies to **every type** (`api`/`etl`/`job`/`agent`/`genie`) and to **every field** — do
**not** drop to plain inline text prompts at any step. `AskUserQuestion` is a multiple-choice
picker; free-text values (slug, names, description, URLs, etc.) are captured via the **"Other"**
option on each question, which lets the user type. Every question needs **at least two
options** (the tool rejects fewer); the **"Other"** free-text choice is added automatically,
so for a pure free-text field give two example/suggestion options and let the user pick "Other"
to type their own. Batch related questions into a single
`AskUserQuestion` screen (up to four questions per screen) so the user answers a compact form,
not a chain of one-at-a-time prompts. If `$ARGUMENTS` already supplies a value, skip that
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

- **Type** (single-select) — five types exist but the picker shows at most four buttons plus
  the auto-added **"Other"**, so **show `genie` as a real button** and demote the least-likely
  bundle type to Other: present `api` · `etl` · `genie` · `agent` as buttons and **name `job`
  explicitly in the question text** (*"Not a button: `job` — a scheduled action
  (export / orchestrate / batch-score / maintain / trigger a pipeline); choose 'Other' and
  type `job`."*). Never bury `genie` in Other. Use **Choosing the type** above to guide the
  user; if they are unsure between `etl` and `job`, apply the "materialize tables vs perform
  an action" test and state which the answer implies before confirming.
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
  --type <api|etl|job|genie|agent> \
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
- Docs live in **`docs/`**: the cross-cutting `PYTHON_STANDARDS.md` plus the per-type file
  (`API_STANDARDS.md` / `PIPELINE_STANDARDS.md` / `JOB_STANDARDS.md` / `AGENT_STANDARDS.md` /
  `GENIE_STANDARDS.md`). The root `README.md` links into `docs/`. Point the
  user at them.
- **Placeholders** — every deferred input is written as a `TODO_SET_` token (e.g.
  `TODO_SET_DEV_WORKSPACE_HOST`, `TODO_SET_CATALOG`, `TODO_SET_TABLE_PREFIX`,
  `TODO_SET_TEAM_NAME`) and listed in the repo's generated `CONFIG.md`. Tell the user to fill
  `CONFIG.md` and run **`{{cmd:scaffold:configure}}`** to apply them in one pass, and name which
  tokens are outstanding.
- **api** — domain schemas live in `schema/models.py`; runtime `command`/`env` live in
  `app.yml` (single source of truth — the app resource in `resources/api.app.yml` no longer
  duplicates them).
- **Bundle types** — remind the user to fill the `TODO_SET_*` values in `databricks.yml`
  (stg/prod hosts, service principals, policy ids) and `team_config.yaml` (repo url, service
  principals) before the first cloud deploy, and to set `CONTROLLER_TRIGGER_TOKEN` in GitLab
  CI/CD variables. Local dev testing: `./bundle.sh`.
- **api** also: set `TODO_SET_WAREHOUSE_ID` / `TODO_SET_CHAT_GATEWAY_URL` in `app.yml`
  (the runtime env), and register the domain with the shared chat gateway service
  (its `domain_configs/`).
- **agent** — no bundle: a Multi-Agent Supervisor deployed by script. Write the routing
  guidance in `supervisor/instructions.md`, set `display_name`/`description` and the `tools`
  list (each: `id`, `type`, `description` + its id) in `supervisor/supervisor.yml`, then
  `./deploy.sh` to create/update the supervisor, attach the tools, and print the working
  query URL (needs `DATABRICKS_HOST` + `DATABRICKS_TOKEN`). Confirm the `supervisor_agents`
  SDK service/tool-type names in `src/deploy.py` first (Preview). Full guidance:
  `docs/AGENT_STANDARDS.md`.
- **genie** — no dummy content is scaffolded: `views/` and `functions/` ship empty and
  `example_queries.yml` / `sample_questions` are commented templates. Point
  `genie-space/space.yml` → `data_sources.tables` at curated gold tables you already own
  (add a backing view under `views/` only if needed), write `description.md` + `instructions.md`,
  optionally fill `example_queries.yml` (question→SQL few-shot pairs — the biggest accuracy
  lever), confirm the `w.genie.*` calls in `deploy_genie.py`, then `./deploy.sh` (local) or
  merge to stg/prod (CI). Full walkthrough: `docs/GENIE_STANDARDS.md` §5–§8.
- To score the deployed stack, scaffold `evaluation/` with `{{cmd:eval:new}}`.
- To add a **single piece** later — or to a repo this command never created — use
  **`{{cmd:scaffold:add}}`**: the `cicd` deploy pipeline, or the `api` surface (`/v1/health` +
  `/v1/info`). It restores what a repo of that type would have had, without touching anything
  else in the repo.

## Example

Every step is an `AskUserQuestion` picker — no inline text prompts:

```
{{cmd:scaffold:new}}
→ [picker] Type / Slug / Repo / Desc?   etl |                       (ONE screen, 4 questions;
   (genie is a button; job named in       signal-quality |           free text via "Other";
    the Type question → Other)             ai-signal-quality-etl |
                                           Monitors cable signal health…
   (display name auto-derived: Signal Quality)
→ [picker] Confirm?                      Proceed / Cancel
✓ Confirm → runs new.py --type etl --slug signal-quality --display-name "Signal Quality" \
              --repo-name ai-signal-quality-etl --description "…"
   (workspace/catalog/table-prefix/team NOT passed → TODO_SET_ placeholders in CONFIG.md;
    fill CONFIG.md, then {{cmd:scaffold:configure}})
```
