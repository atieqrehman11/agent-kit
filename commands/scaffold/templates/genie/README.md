# TPLVAR_DISPLAY_NAME

TPLVAR_DESCRIPTION

**Type:** `genie` — a **Genie space**, deployed via the Genie management API (there is no
DAB bundle for Genie). `genie-space/space.yml` is the definition; the long-form description
and instructions live in their own `.md` files it points to. `deploy_genie.py` assembles
them into the `serialized_space` payload and calls createspace / updatespace.

## Deployment

| Target | How |
|---|---|
| **local** | `./deploy.sh` — applies the backing-view DDL, then create/update the space |
| **stg / prod** | merge to the `stg` / `prod` branch — CI runs `deploy_genie.py` |

The Genie management API is recent (Public Preview) — confirm the `w.genie.*` method and
`serialized_space` field names for your workspace, then uncomment the API calls in
`deploy_genie.py`. See https://docs.databricks.com/api/workspace/genie/createspace

## Layout

```
genie-space/space.yml       definition: title, warehouse_id, data_sources,
                            sample_questions, space_id, + pointers to the .md files
genie-space/description.md    long-form space Description (edited as prose)
genie-space/instructions.md   long-form space Instructions (edited as prose)
genie-space/example_queries.yml  OPTIONAL curated question -> SQL pairs (few-shot);
                            ships as an empty commented template
genie-space/views/            EMPTY by default — add a backing view only if needed
genie-space/functions/        EMPTY by default — UC-function DDL for the space
deploy_genie.py             assemble serialized_space + create/update via the API
deploy.sh                   local one-shot (pip install + apply DDL + deploy)
.gitlab-ci.yml              validate space.yml → apply DDL → deploy on stg/prod
docs/                       all repo docs (standards, guides)
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

On first create, `deploy_genie.py` writes the new `space_id` back into `space.yml`; commit
that so later runs update the same space.
