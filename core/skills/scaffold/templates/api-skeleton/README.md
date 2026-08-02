# TPLVAR_DISPLAY_NAME

TPLVAR_DESCRIPTION

**Type:** `api` — Deployed as a **Databricks App** (`resources.apps`).

This repo is a single Databricks Asset Bundle. `resources.<apps|jobs|pipelines>` is the
DAB schema collection key (always plural, even for one resource); the single resource key
under it is defined in `resources/`.

## Deployment

| Target | How | Where |
|---|---|---|
| **dev** | `./bundle.sh` (local dev loop) | your laptop → dev workspace |
| **stg** | merge to the `stg` branch | CI/CD controller → stg workspace |
| **prod** | merge to the `prod` branch | CI/CD controller → prod workspace |

`bundle.sh` deploys to **dev only** on purpose. stg/prod are cloud deploys owned by the
shared CI/CD controller (`.gitlab-ci.yml`). Set `CONTROLLER_TRIGGER_TOKEN` in
GitLab → Settings → CI/CD → Variables before the first cloud deploy.

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

databricks.yml          bundle name + generated uuid + dev/stg/prod targets
resources/              the one resource (apps | pipelines | jobs)
.gitlab-ci.yml          controller trigger (validate -> stg -> prod)
team_config.yaml        controller registration (bundle_name, uuid, url)
run_resources.yml       resource keys to run after deploy
docs/                   all repo docs (standards, conformance sheets)
CONFIG.md               one-page fill-in sheet for every TODO_SET_* placeholder
```

Calls go one way: `routers/` → `services/` → `repositories/`. A router never queries
anything directly, a service never sees an HTTP type, and no route builds an error body —
`core/handlers.py` owns every error response.

## Standards

Docs live in [`docs/`](docs/). Three non-overlapping layers, all applied when writing code here:

- [`docs/PYTHON_STANDARDS.md`](docs/PYTHON_STANDARDS.md) — code style (PEP 8, type hints, Ruff, testing).
- [`docs/SERVICE_STRUCTURE_STANDARDS.md`](docs/SERVICE_STRUCTURE_STANDARDS.md) — how the service is
  arranged: layering, where models live, one exception hierarchy, log levels from config, and no
  hardcoded prompts or thresholds.
- [`docs/API_STANDARDS.md`](docs/API_STANDARDS.md) — the contract on the wire for this resource type.

Each ships its audit list beside it as `*_CONFORMANCE.md` — that is what a reviewer walks, and
what to check yourself before opening a merge request.

Run `ruff check` and `ruff format` before committing.

## Before first deploy

Every infrastructure placeholder (stg/prod hosts, service principals, policy ids, team,
repo url, and any runtime env) is listed in one place — [`CONFIG.md`](CONFIG.md). Fill in
the values there, then apply them across the repo:

```
{{cmd:scaffold:configure}}          # or: python3 <commands>/scaffold/configure.py --repo .
```

This replaces the `TODO_SET_*` tokens in `databricks.yml`, `team_config.yaml`, and the
rest of the tree. The bundle `uuid` is already generated — do not change it.
