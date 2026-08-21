# TPLVAR_DISPLAY_NAME

TPLVAR_DESCRIPTION

**Type:** `api` — Deployed as a **Databricks App** (`resources.apps`).

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
app.py                  entry point — wiring only, no logic
core/                   config (validated Settings), logging setup, exceptions,
                        handlers, request-id + access-log middleware
routers/                boundary — platform.py (health/info) + domain.py
services/               business logic; knows nothing about HTTP
repositories/           all I/O — warehouse, object store, external HTTP, LLM
schema/                 every model: request, response, domain
app.yml                 runtime env for the App (LOG_LEVEL, CORS_ORIGINS, …)

databricks.yml          (deploy aspect) bundle name + uuid + dev/stg/prod targets
resources/              (deploy aspect) the one resource (apps|pipelines|jobs)
.gitlab-ci.yml          (gitlab aspect) controller trigger (validate->stg->prod)
team_config.yaml        controller registration (bundle_name, uuid, url)
run_resources.yml       (deploy aspect) resource keys to run after deploy
docs/                   repo docs (guides, runbooks) — standards live in agent-kit
CONFIG.md               one-page fill-in sheet for every TODO_SET_* placeholder
```

Calls go one way: `routers/` → `services/` → `repositories/`. A router never queries
anything directly, a service never sees an HTTP type, and no route builds an error body —
`core/handlers.py` owns every error response.

## Configuration

Configuration is loaded and validated **once** at startup into the typed `Settings` object
in `core/config.py`, and fails loudly on a missing key. Nothing else in the repo calls
`os.getenv`.

Values arrive from the environment: `resources/api.app.yml` supplies them when deployed,
`.env` locally. Anything that differs per environment is a **bundle variable** in
`databricks.yml`, overridden per target — a literal at a callsite survives the override
untouched, so a stg deploy would read dev's data and report success. No prompt, threshold,
endpoint or model parameter belongs at a callsite either; it belongs here.

### Before first deploy

Every infrastructure placeholder (stg/prod hosts, service principals, policy ids, team,
repo url, and any runtime env) is listed in one place — [`CONFIG.md`](CONFIG.md). Fill in
the values there, then apply them across the repo:

```
{{cmd:scaffold:configure}}          # or: python3 <commands>/scaffold/configure.py --repo .
```

This replaces the `TODO_SET_*` tokens across the tree. The bundle `uuid` is already
generated — do not change it.

`wheels/` must be vendored and **committed** before the first deploy — the Apps build
environment has no network. See [`wheels/README.md`](wheels/README.md).

## Verify

```bash
./run_local.sh              # serve on :8000 with reload
curl localhost:8000/v1/health
open localhost:8000/docs    # the generated OpenAPI contract
ruff check . && ruff format --check .
```

**No tests ship with this skeleton, and that is a gap to close, not a licence.** Add them
under `tests/` as you add logic, and mock at the I/O seam — the repository class — never
inside the logic under test. What to cover first: every branch a route or service adds,
each domain exception actually being raised, and both sides of any threshold or default.

`./run_local.sh deploy` validates the bundle before deploying, which catches a malformed
descriptor and an undeclared `--var`. It does not exercise a single endpoint.

## Deployment

| Target | How | Where |
|---|---|---|
| **dev** | `./run_local.sh deploy` (local dev loop) | your laptop → dev workspace |
| **stg** | merge to the `stg` branch | CI/CD controller → stg workspace |
| **prod** | merge to the `prod` branch | CI/CD controller → prod workspace |

`run_local.sh` deploys to **dev only** on purpose. stg/prod are cloud deploys owned by the
shared CI/CD controller (`.gitlab-ci.yml`). Set `CONTROLLER_TRIGGER_TOKEN` in
GitLab → Settings → CI/CD → Variables before the first cloud deploy.
