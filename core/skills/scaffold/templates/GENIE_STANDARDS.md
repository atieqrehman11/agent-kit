# Genie Standards — __ORG_PREFIX__Genie Space Reference

Standard for the `genie` repo type: a Databricks **Genie space** deployed via the Genie
**management API** (`createspace` / `updatespace`). There is no DAB bundle for Genie —
`deploy_genie.py` assembles the payload from the repo files and calls the API.

The **repo is authoritative**: the space is (re)deployed *from* these files. All
answer-quality tuning (description, instructions, example queries, backing view) lives here.

---

## 1. Canonical layout

```
genie-space/
├── space.yml            the DEFINITION — space_id, title, warehouse_id, data_sources,
│                         sample_questions, + pointers to the prose / example files
├── description.md        the space Description as PROSE (pointed to by space.yml)
├── instructions.md       the space Instructions as PROSE (pointed to by space.yml)
├── example_queries.yml   OPTIONAL curated question -> SQL pairs (few-shot). Ships as a
│                         commented TEMPLATE with an empty list — nothing sent until filled
├── views/                EMPTY by default — add a bespoke backing-view .sql only if needed
└── functions/            EMPTY by default — UC-function DDL to attach to the space
CHANGELOG.md              version → date → eval baseline → what changed
deploy_genie.py           assemble serialized_space + create/update via the API
deploy.sh                 local one-shot: pip install + apply DDL + deploy
.gitlab-ci.yml            validate space.yml → apply DDL → deploy on stg/prod merge
GENIE_STANDARDS.md        this file
```

> **No dummy content is scaffolded.** `views/` and `functions/` start empty and
> `example_queries.yml` / `sample_questions` ship as commented templates. A Genie space
> points at *curated tables you already own*; you supply the data sources and examples.

---

## 2. Definition vs prose — keep them apart

**Structured wiring lives in `space.yml`; long text lives in the files it points to.**
The Genie Description and Instructions are multi-paragraph prose; inlining them as YAML
strings is painful to write and review, and a formatter can reflow them. So:

- `space.yml` holds machine-readable fields only: `space_id`, `title`, `warehouse_id`,
  `data_sources`, `sample_questions`, and the `*_file` pointers.
- `description.md`, `instructions.md`, and `example_queries.yml` hold the content.
  `deploy_genie.py` reads them and folds them into the payload.

---

## 3. The `serialized_space` payload

`deploy_genie.py` maps the repo files to the API's `serialized_space` (version 2):

| Payload field | Source | Notes |
|---|---|---|
| `title` | `space.yml: title` | |
| `description` | contents of `description.md` | verbatim |
| `instructions` | contents of `instructions.md` | verbatim |
| `data_sources` | `space.yml: data_sources` | tables + metric_views |
| `sample_questions` | `space.yml: sample_questions` | each gets a 32-char hex id |
| `example_queries` | `example_queries.yml` | **only if entries present** — see §6 |

The example-queries field name is a **Public-Preview API detail** — confirm it for your
workspace version and adjust the mapping in `deploy_genie.py` if it differs.

---

## 4. Create vs update

- **`space_id` empty → CREATE** a new space. On success the deploy script writes the new id
  back into `space.yml` — **commit that id** so later runs update the same space.
- **`space_id` set → UPDATE** the existing space in place.

This makes the deploy idempotent: the first run creates, every later run updates.

---

## 5. Data sources — point at curated tables

A Genie space answers questions **over curated tables you already own** — normally the
**gold** layer of a use-case ETL repo. Genie should never read raw or bronze data.

- **Default: list existing tables directly** in `space.yml: data_sources.tables`
  (e.g. `your_catalog.gold.customer_orders`). No SQL to write in this repo.
- **Optional bespoke view.** If no single existing table fits (you need a join, a rename,
  or a narrowed column set), write re-appliable `CREATE OR REPLACE VIEW` DDL under
  `views/<name>.sql`, then list that view under `data_sources.tables`. Expose exactly the
  columns Genie should query, with clear names it can reason about. **Skip this** when
  existing tables already fit — do not add a view for its own sake.
- **UC functions** the space uses live under `functions/` as `CREATE OR REPLACE FUNCTION`
  DDL and are listed in `space.yml: uc_functions`.
- **DDL is applied before the space is created/updated** (`deploy.sh` / CI run with
  `--apply-ddl`), so anything under `views/` and `functions/` exists first.

---

## 6. Example SQL queries (the biggest accuracy lever)

Curated **question → trusted-SQL** pairs teach Genie the joins, filters, and column choices
your data needs. They are the single most effective tuning knob for a space, and are
**optional** — the space works without them, but accuracy improves sharply with a handful of
good ones.

- The scaffold ships `genie-space/example_queries.yml` as a **commented template** with an
  empty `example_queries: []` list, so nothing is sent until you add entries.
- Each entry pairs one natural-language `question` with the exact single-statement `sql`
  that answers it against this space's `data_sources`:

  ```yaml
  example_queries:
    - question: "How many active customers are there by region?"
      sql: |
        SELECT region, COUNT(*) AS active_customers
        FROM your_catalog.gold.customers
        WHERE status = 'ACTIVE'
        GROUP BY region
        ORDER BY active_customers DESC
  ```

- Guidance: cover the questions users actually ask; make every query **run and return the
  right answer** (paste from a validated notebook); reference only tables in `data_sources`;
  prefer 5–15 high-quality pairs over many low-quality ones.
- `deploy_genie.py` reads the file via `space.yml: example_queries_file` and includes any
  entries in the payload. Leaving the list empty is fine and sends nothing.

---

## 7. Sample questions

`space.yml: sample_questions` are the starter chips shown in the Genie UI. Ship them as
real, answerable questions (the scaffold lists a `TODO` placeholder plus commented examples).
These are display prompts only — they do **not** carry SQL; that is what §6 example queries
are for.

---

## 8. Building the space (make it real)

The scaffold is a skeleton. To turn it into a working space:

1. **Point at your data** — `space.yml: data_sources.tables` (§5).
2. **(Optional) add a backing view** under `views/` only if needed (§5).
3. **Write the prose** — `description.md` (what the space covers) and `instructions.md`
   (how Genie should answer: joins, filters, business definitions, units, caveats).
4. **Add example queries** — fill `example_queries.yml` with validated question → SQL
   pairs (§6). Highest-leverage step for accuracy.
5. **Set `sample_questions`** to real starter questions (§7).
6. **Fill config** — `warehouse_id` (and `catalog`, if referenced) via `CONFIG.md` →
   `{{cmd:scaffold:configure}}`.
7. **Confirm the API calls** — verify the `w.genie.*` method and `serialized_space` field
   names (Public Preview), then uncomment them in `deploy_genie.py`.
8. **Deploy** — `./deploy.sh` locally, or merge to `stg` / `prod` for CI.

---

## 9. Deployment

| Target | How |
|---|---|
| **local** | `./deploy.sh` — pip install, apply DDL, then create/update the space |
| **stg / prod** | merge to the `stg` / `prod` branch — CI runs `deploy_genie.py` |

Auth uses the default Databricks SDK chain (`DATABRICKS_HOST` + token, or a CLI profile)
plus a `warehouse_id` in `space.yml`.

> The Genie management API is recent (**Public Preview**). Confirm the exact SDK method and
> `serialized_space` field names for your workspace version before the first deploy — the
> scaffold ships the `w.genie.*` calls commented with a doc link.
> See https://docs.databricks.com/api/workspace/genie/createspace

---

## 10. Versioning & the eval loop

- Keep `CHANGELOG.md`: version → date → eval baseline → what changed, one row per deploy.
- The loop: **edit `genie-space/` → deploy → run `evaluation/` → record the baseline**.
  Scaffold the eval area with `{{cmd:eval:new}}` and point the spec at the deployed space.
