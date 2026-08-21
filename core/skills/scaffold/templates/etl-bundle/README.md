# TPLVAR_DISPLAY_NAME

TPLVAR_DESCRIPTION

**Type:** `etl` — A **Lakeflow declarative pipeline** (`resources.pipelines`).

This repo is a single Databricks Asset Bundle. `resources.<apps|jobs|pipelines>` is the
DAB schema collection key (always plural, even for one resource); the single resource key
under it is defined in `resources/`.

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
databricks.yml          (deploy aspect) bundle name + uuid + dev/stg/prod targets
resources/              (deploy aspect) the one resource (apps|pipelines|jobs)
.gitlab-ci.yml          (gitlab aspect) controller trigger (validate->stg->prod)
team_config.yaml        controller registration (bundle_name, uuid, url)
run_resources.yml       (deploy aspect) resource keys to run after deploy
docs/                   repo docs (guides, runbooks) — standards live in agent-kit
CONFIG.md               one-page fill-in sheet for every TODO_SET_* placeholder
```

## Configuration

Every per-environment value is a **bundle variable** in `databricks.yml`, overridden per
target. Nothing under `src/` names a catalog, schema, volume or endpoint — a literal there
survives the target override untouched, so a stg run would read dev's data and report
success.

### Before first deploy

Every infrastructure placeholder (stg/prod hosts, service principals, policy ids, team,
repo url, and any runtime env) is listed in one place — [`CONFIG.md`](CONFIG.md). Fill in
the values there, then apply them across the repo:

```
{{cmd:scaffold:configure}}          # or: python3 <commands>/scaffold/configure.py --repo .
```

This replaces the `TODO_SET_*` tokens across the tree. The bundle `uuid` is already
generated — do not change it.

## Verify

```bash
./run_local.sh            # databricks bundle validate -t dev (a pipeline has no local run)
ruff check . && ruff format --check .
```

Bundle validation catches a malformed descriptor and an undeclared `--var`. It does **not**
run your code, so a green run says the bundle would deploy, not that a stage is correct.

**Add tests as you add logic.** Put them in `tests/`, runnable without Spark or a
workspace. A `@dp.table` function is not testable as written — extract the transform it
wraps into a plain function and test that; the decorated shell stays untested on purpose.
A repo whose only gate is `bundle validate` has no way to catch a wrong threshold, an
inverted condition, or an expectation that quarantines the wrong rows.

## Deployment

| Target | How | Where |
|---|---|---|
| **dev** | `./run_local.sh deploy` (local dev loop) | your laptop → dev workspace |
| **stg** | merge to the `stg` branch | CI/CD controller → stg workspace |
| **prod** | merge to the `prod` branch | CI/CD controller → prod workspace |

`run_local.sh` deploys to **dev only** on purpose. stg/prod are cloud deploys owned by the
shared CI/CD controller (`.gitlab-ci.yml`). Set `CONTROLLER_TRIGGER_TOKEN` in
GitLab → Settings → CI/CD → Variables before the first cloud deploy.
