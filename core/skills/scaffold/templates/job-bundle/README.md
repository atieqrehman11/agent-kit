# TPLVAR_DISPLAY_NAME

TPLVAR_DESCRIPTION

**Type:** `job` — A **scheduled Databricks Job** (`resources.jobs`).

This repo is a single Databricks Asset Bundle. `resources.<apps|jobs|pipelines>` is the
DAB schema collection key (always plural, even for one resource); the single resource key
under it is defined in `resources/`.

## Layout

```
databricks.yml          bundle name + generated uuid + dev/stg/prod targets,
                        and every per-environment value as a variable
resources/job.job.yml   the one job resource — the task chain and the schedule
src/task_0N_<verb>.py   one file per stage; parameters arrive as widgets
.gitlab-ci.yml          controller trigger (validate -> stg -> prod)
run_resources.yml       empty — the job runs on its schedule, not on deploy
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
./run_local.sh            # run the job entrypoint locally
ruff check . && ruff format --check .
```

`./run_local.sh deploy` validates the bundle first, which catches a malformed descriptor
and an undeclared `--var`. A local entrypoint run exercises one stage against whatever
credentials you have — useful, but it is not a test: nothing asserts the result.

**Add tests as you add logic.** Put them in `tests/`, runnable without Spark or a
workspace — a pure function extracted from a stage is testable, the stage wrapper is not.
A repo whose only gate is `bundle validate` has no way to catch a wrong threshold or an
inverted condition before it reaches data.

## Deployment

| Target | How | Where |
|---|---|---|
| **dev** | `./run_local.sh deploy` (local dev loop) | your laptop → dev workspace |
| **stg** | merge to the `stg` branch | CI/CD controller → stg workspace |
| **prod** | merge to the `prod` branch | CI/CD controller → prod workspace |

`run_local.sh` deploys to **dev only** on purpose. stg/prod are cloud deploys owned by the
shared CI/CD controller (`.gitlab-ci.yml`). Set `CONTROLLER_TRIGGER_TOKEN` in
GitLab → Settings → CI/CD → Variables before the first cloud deploy.
