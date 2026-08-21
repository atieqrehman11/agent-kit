# TPLVAR_DISPLAY_NAME

TPLVAR_DESCRIPTION

**Type:** `genie` — a Databricks **Genie space**, deployed as an Asset Bundle.
DAB exposes a `genie_spaces` resource (CLI 1.3.0+, `engine: direct`), so this
deploys through the shared CI/CD controller like every other bundle: no deploy
script, and no workspace token in CI.

The **repo is authoritative**. The space is redeployed *from* these files, so
anything tuned in the Genie UI is overwritten on the next deploy. All
answer-quality work — instructions, example queries, the backing views — lives
here.

## What is in this repo, and what is not

`{{cmd:scaffold:new}}` writes the application code and nothing that binds the repo to a
workspace. The deploy descriptor and the pipeline are added later, each once its
prerequisite is actually met — they are not missing by accident:

| Add | Brings | When |
|---|---|---|
| `{{cmd:scaffold:add}} --aspect deploy` | `databricks.yml`, `resources/`, `run_local.sh`, `run_resources.yml` | the bundle name + uuid are in the platform team's registry and the stg/prod service principals exist |
| `{{cmd:scaffold:add}} --aspect gitlab` | `.gitlab-ci.yml` and the GitLab project setup scripts | CI/CD onboarding is done and the group-level `CONTROLLER_TRIGGER_TOKEN` is set |
| `{{cmd:scaffold:add}} --aspect specs` | `docs/specs/README.md` | the team adopts the per-feature spec convention |

Sections below marked *(deploy aspect)* describe the repo **after** that add. Until then
there is nothing to deploy and no pipeline to fire — which is deliberate: a `databricks.yml`
full of `TODO_SET_` values looks deployable and is not, and a pipeline pushed before
registration fails the controller's governance stage rather than this repo's own.

## Layout

```
src/                     what the space is made of
├── space.yml              the manifest — just the instruction id
├── instructions.md        how Genie should answer (sent byte-verbatim)
├── data_sources.yml       the tables and views it may query
├── sql_functions.yml      UC functions it may call
├── example_queries.yml    curated question -> trusted-SQL pairs
├── views/*.sql            DDL for any bespoke backing view
└── functions/*.sql        DDL for the functions above
python/
├── build_space.py         assembles src/ into the artifact
└── validate.py            checks src/ — no credentials, no network
generated/               built, COMMITTED, never hand-edited
resources/genie.yml      (deploy aspect) the DAB resource — title, warehouse_id
databricks.yml           (deploy aspect) per-environment values; per-target catalog
docs/                    changelog — standards live in agent-kit
```

## Configuration

Every per-environment value — catalog, schema, warehouse, space title — lives in
`databricks.yml`, set per target, and nowhere else. Nothing under `src/` names a catalog:
everything is `${catalog}.${schema}`, substituted at build time.

That substitution is why there is **one built artifact per environment**. DAB resolves
`${var.*}` inside an inline `serialized_space` but reads a `file_path` target verbatim, so
the catalog is baked in at build and `${bundle.target}` picks the file.

### Before first deploy

Fill [`CONFIG.md`](CONFIG.md), then apply it:

```
{{cmd:scaffold:configure}}          # or: python3 <commands>/scaffold/configure.py --repo .
```

## Verify

```bash
python3 python/validate.py     # the declaration alone — no credentials, no network
./run_local.sh                 # the above, then build + `databricks bundle validate`
```

The validator refuses what would deploy and be wrong:


- Every identifier starts with `${catalog}.${schema}.` — a literal catalog
  survives substitution untouched, so a stg deploy would silently read dev.
- No `space_id` / `genie_space_id` in `src/`. DAB owns the space's identity
  through the resource key in `resources/genie.yml`; a committed id is deploy
  state the repo must not hold.
- Renaming that resource key **destroys and recreates** the space, losing its id
  and every conversation in it.

None of that says the space **answers** correctly, which is the risk that matters for a
non-deterministic system. See [Evaluation](#evaluation) — and note that a change to
`instructions.md` or `example_queries.yml` is a behaviour change with nothing to compile
and no test to break.

## The build step, and why it exists

DAB resolves `${var.*}` inside an *inline* `serialized_space`, but reads a
`file_path` payload **verbatim**. So the catalog cannot be a variable in the
artifact — it is baked in at build time, and `${bundle.target}` picks which file
deploys:

```
src/  --build_space.py --env stg-->  generated/space.stg.json  --DAB-->  workspace
```

That is also why `generated/` is committed. The controller clones the repo fresh
and runs no project scripts, so what is in git is what deploys.

**Build every environment before promoting:**

```bash
./run_local.sh all        # builds dev, stg and prod, then validates
```

Building only `dev` and merging leaves stg deploying whatever artifact was
committed last.

## Deployment

| Target | How |
|---|---|
| **dev** | `./run_local.sh deploy` — build, validate, `bundle deploy -t dev` |
| **stg** | merge to the `stg` branch — the controller deploys |
| **prod** | merge to `prod`, then press play in Build → Pipelines |

Never run `databricks bundle deploy -t stg|prod` by hand — that is the
controller's job.

## The DDL is not deployed

DAB has no resource for arbitrary SQL, so nothing in this pipeline runs
`src/views/*.sql` or `src/functions/*.sql`. Apply them to the catalog yourself
before the space can answer anything. A space whose functions do not exist
deploys perfectly cleanly and then fails every question that needs one.

## Evaluation

The loop is: edit `src/` → build → deploy → run `evaluation/` → record the
baseline in `docs/CHANGELOG.md`. Scaffold the suite with `{{cmd:eval:new}}`.
