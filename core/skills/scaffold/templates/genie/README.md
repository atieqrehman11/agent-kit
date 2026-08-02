# TPLVAR_DISPLAY_NAME

TPLVAR_DESCRIPTION

**Type:** `genie` — a **Genie space**, deployed via the Genie management API (there is no
DAB bundle for Genie). `genie-space/space.yml` is the definition; the long-form description
and instructions live in their own `.md` files it points to. `src/deploy.py` assembles
them into the `serialized_space` payload and calls createspace / updatespace.

## Deployment

| Target | How |
|---|---|
| **local (dev)** | `./deploy.sh` — applies the backing-view DDL, then reconciles the space |
| **stg / prod** | merge to the `stg` / `prod` branch — CI runs `src/deploy.py --env <branch>` |

**No id is stored in this repo.** The space is found by title, `"<title> [ENV]"`, in the
workspace `DATABRICKS_HOST` points at — one match is updated, none creates it, several
refuse. See [`docs/GENIE_STANDARDS.md`](docs/GENIE_STANDARDS.md) §4.

The Genie management API is Public Preview — confirm the `serialized_space` field names for
your workspace version. See https://docs.databricks.com/api/workspace/genie/createspace

## Layout

```
genie-space/space.yml       definition: title, warehouse_id, data_sources,
                            sample_questions, + pointers to the .md files
genie-space/description.md    long-form space Description (edited as prose)
genie-space/instructions.md   long-form space Instructions (edited as prose)
genie-space/example_queries.yml  OPTIONAL curated question -> SQL pairs (few-shot);
                            ships as an empty commented template
genie-space/views/            EMPTY by default — add a backing view only if needed
genie-space/functions/        EMPTY by default — UC-function DDL for the space
src/validate.py             check space.yml — no credentials, no network
src/deploy.py               assemble serialized_space + reconcile via the API
deploy.sh                   local one-shot (pip install + apply DDL + deploy)
.gitlab-ci.yml              two jobs, each one line: run validate.py, run deploy.py
docs/                       all repo docs (standards, guides)
```

Check it before pushing — no credentials needed, same check CI runs first:

```
python src/validate.py
```

`views/`, `functions/`, `example_queries.yml`, and `sample_questions` ship **empty /
as templates on purpose** — no dummy content is generated. A Genie space points at
*curated tables you already own*. The full walkthrough for turning this skeleton into a
working space — data sources, optional backing views, example SQL queries (the biggest
accuracy lever), sample questions, and deploy — is in
[`docs/GENIE_STANDARDS.md`](docs/GENIE_STANDARDS.md) §5–§8.

## Standards

Docs live in [`docs/`](docs/). Two non-overlapping layers, both applied when writing code here:

- [`docs/PYTHON_STANDARDS.md`](docs/PYTHON_STANDARDS.md) — code style (PEP 8, type hints, Ruff, testing).
- [`docs/GENIE_STANDARDS.md`](docs/GENIE_STANDARDS.md) — how to build and deploy the Genie space.

Run `ruff check` and `ruff format` before committing.

`space.yml` is a declaration, not a record: it holds no `space_id`. Renaming `title`
re-points the deploy at a different space, so treat it as the space's identity.
