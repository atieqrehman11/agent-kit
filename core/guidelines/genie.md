---
name: genie
kind: guideline
description: >
  Standards for Genie spaces: views, functions, instructions and benchmark coverage. Applies
  when building or reviewing a Genie space.
applies_to:
  - "**/resources/genie*.yml"
  - "**/src/space.yml"
  - "**/src/instructions.md"
  - "**/src/data_sources.yml"
  - "**/src/example_queries.yml"
  - "**/src/sql_functions.yml"
  - "**/python/build_space.py"
---

# Genie Standards — __ORG_PREFIX__Genie Space Reference

Standard for the `genie` repo type: a Databricks **Genie space** deployed as an Asset
Bundle. DAB exposes a `genie_spaces` resource (CLI 1.3.0+, `engine: direct`), so a space
deploys through the shared CI/CD controller like every other bundle — no deploy script, no
workspace token in CI.

The **repo is authoritative**: the space is (re)deployed *from* these files. All
answer-quality tuning (description, instructions, example queries, backing view) lives here.

---

## 1. Canonical layout

```
src/                     what the space is made of
├── instructions.md        how Genie should answer — prose, sent verbatim
├── example_queries.yml    curated question -> SQL pairs, each with an id
├── data_sources.yml       tables + per-column tuning
├── sql_functions.yml      UC functions to attach
├── space.yml              the instruction id
├── views/                 backing-view DDL, only if an existing table will not do
└── functions/             UC-function DDL
python/
├── build_space.py         assembles src/ into the artifact
└── validate.py            refuses what would deploy and be wrong
run_local.sh             build + validate; `deploy` also deploys to dev
generated/               built, committed, never hand-edited
└── space.{dev,stg,prod}.json
resources/genie.yml      the DAB resource — title, warehouse_id, description, file_path
databricks.yml           targets, run_as, per-environment values
run_resources.yml        empty — a space is live as soon as it deploys
```

**The artifact is committed.** The controller clones the repo fresh and runs no project
scripts, so anything not in the commit does not exist to it.

**One artifact per environment.** DAB resolves `${var.*}` inside an inline
`serialized_space` but reads a `file_path` target verbatim, so the catalog is baked in at
build time and `${bundle.target}` selects the file.

> **No dummy content is scaffolded.** `views/` and `functions/` start empty and
> `example_queries.yml` ships as a commented template. A Genie space points at *curated
> tables you already own*; you supply the data sources and examples.

---

## 2. One file per kind of content

Structured wiring and long prose are separate files, and each names one kind of thing:

| File | Holds |
|---|---|
| `data_sources.yml` | the tables and their per-column tuning |
| `sql_functions.yml` | the UC functions to attach |
| `example_queries.yml` | question → SQL pairs |
| `instructions.md` | the instruction prose, sent byte-verbatim |
| `resources/genie.yml` | `description`, `title`, `warehouse_id` — DAB fields, not payload |

Prose is sent byte-for-byte: a reflowed paragraph or an added trailing newline is a content
change. Keep it in `.md`, and do not let a formatter touch it.

---

## 3. The `serialized_space` payload

`build_space.py` maps `src/` to the API's `serialized_space` (version 2), written to
`generated/space.<env>.json`:

| Payload field | Source |
|---|---|
| `data_sources` | `data_sources.yml` |
| `instructions.text_instructions` | `instructions.md` + the id in `space.yml` |
| `instructions.example_question_sqls` | `example_queries.yml` |
| `instructions.sql_functions` | `sql_functions.yml` |

`title` and `description` are **not** in the payload — the API takes them as separate
fields, so they live in `resources/genie.yml`.

### Ids are authored here

Every instruction, example and function carries a 32-hex id (lowercase, no hyphens). A
create is **rejected** without one:

```
example_question_sql.id must be provided and non-empty.
Expected lowercase 32-hex UUID without hyphens.
```

The platform stores whatever it is sent, so ids are minted in the repo and committed —
that is what makes a redeploy edit each entry in place rather than drop and re-add it.
`build_space.py` mints any that are missing and writes them back into the source file.

---

## 4. Identity and environments

DAB owns identity. The resource key in `resources/genie.yml` is what the bundle tracks;
renaming it destroys and recreates the space, losing its `space_id` — which is its URL, and
what an App binds to via `genie_space.space_id`. Do not rename it once deployed.

**Every per-environment value lives in `databricks.yml`, and nowhere else:**

| | Where |
|---|---|
| Which workspace | `targets.<env>.workspace.host` |
| Which title | `${var.space_title}`, overridden per target |
| Which warehouse | `${var.warehouse_id}`, overridden per target |
| Which catalog | `${var.catalog}` — read by the build, baked into the artifact |

`build_space.py` reads `catalog` and `schema` from the target in `databricks.yml`,
resolving overrides over defaults exactly as DAB does, so the artifact is built from the
same values the deploy will use.

`run_as` is required on `stg` and `prod` — the controller extracts it and fails governance
without it. `dev` has none, because you deploy it yourself.

---

## 5. Data sources — point at curated tables

A Genie space answers questions **over curated tables you already own** — normally the
**gold** layer of a use-case ETL repo. Genie should never read raw or bronze data.

- **Default: list existing tables directly** in `src/data_sources.yml`
  (e.g. `your_catalog.gold.customer_orders`). No SQL to write in this repo.
- **Optional bespoke view.** If no single existing table fits (you need a join, a rename,
  or a narrowed column set), write re-appliable `CREATE OR REPLACE VIEW` DDL under
  `src/views/<name>.sql`, then list that view in `src/data_sources.yml`. Expose exactly the
  columns Genie should query, with clear names it can reason about. **Skip this** when
  existing tables already fit — do not add a view for its own sake.
- **UC functions** the space uses live under `src/functions/` as `CREATE OR REPLACE FUNCTION`
  DDL and are listed in `src/sql_functions.yml`. A space may also *declare* a function whose
  DDL is owned by the repo that owns the tables it reads; say which repo that is in
  `sql_functions.yml`, because nothing else records the dependency.
- **The bundle does not deploy the DDL.** DAB has no resource for arbitrary SQL, so every view
  and function must be applied to the catalog separately — by hand, or by a stage of the
  owning repo — and must exist before the space is deployed. The space attaches by name, and
  the create API does not validate functions the way it validates tables, so a space whose
  functions are missing deploys clean and fails only when someone asks.

---

## 6. Example SQL queries (the biggest accuracy lever)

Curated **question → trusted-SQL** pairs teach Genie the joins, filters, and column choices
your data needs. They are the single most effective tuning knob for a space, and are
**optional** — the space works without them, but accuracy improves sharply with a handful of
good ones.

- The scaffold ships `src/example_queries.yml` as a **commented template** with an
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
- `build_space.py` reads `src/example_queries.yml` and includes any
  entries in the payload. Leaving the list empty is fine and sends nothing.

---

## 7. Sample questions

The `serialized_space` v2 schema has **no field** for them, so they cannot be deployed from
the repo. Anything set in the UI is display-only and is not tracked here.

---

## 8. Building the space (make it real)

The scaffold is a skeleton. To turn it into a working space:

1. **Point at your data** — `src/data_sources.yml` (§5).
2. **(Optional) add a backing view** under `src/views/` only if needed (§5).
3. **Write the prose** — `src/instructions.md` (how Genie should answer: joins, filters,
   business definitions, units, caveats). What the space *covers* is the `description` DAB
   field in `resources/genie.yml`, not a file in `src/`.
4. **Add example queries** — fill `example_queries.yml` with validated question → SQL
   pairs (§6). Highest-leverage step for accuracy.
5. **Set `sample_questions`** to real starter questions (§7).
6. **Fill config** — `warehouse_id` (and `catalog`, if referenced) via `CONFIG.md` →
   `{{cmd:scaffold:configure}}`.
7. **Build and check it** — `./run_local.sh`. Builds every artifact and validates
   the bundle; needs no credentials for the build itself.
8. **Deploy** — `./run_local.sh deploy` for dev, or merge to `stg` / `prod`.

---

## 9. Deployment

| Target | How |
|---|---|
| **local (dev)** | `./run_local.sh deploy` — build, validate, `bundle deploy -t dev` |
| **stg / prod** | merge to the `stg` / `prod` branch — the pipeline triggers the DAB controller |

Local deploys use your CLI profile. stg and prod use the controller's service principal —
there is no workspace token in CI, only `CONTROLLER_TRIGGER_TOKEN`. The workspace comes
from `targets.<env>.workspace.host` (§4).

`warehouse_id` is **required** by the API to create a space and cannot be left unset; it is
optional only on an update.

> The Genie management API is **Public Preview**. Confirm the `serialized_space` field names
> for your workspace version before the first deploy.
> See https://docs.databricks.com/api/workspace/genie/createspace

---

## 10. Versioning & the eval loop

- Keep `CHANGELOG.md`: version → date → eval baseline → what changed, one row per deploy.
- The loop: **edit `src/` → build → deploy → run `evaluation/` → record the baseline**.
  Scaffold the eval area with `{{cmd:eval:new}}` and point the spec at the deployed space.

---

## 11. Benchmark coverage — the accuracy gate

A Genie space has no unit tests, so **the benchmark set is the test suite**. Without one there is
no way to tell a tuning improvement from a regression, and every change in this repo is a
behaviour change to a non-deterministic system.

**Minimum, for any space that anyone else will query:**

- **A handful of held-out cases.** Example queries (§6) are *training* signal sent to the space;
  benchmark questions are evaluation. A question used as an example query must not also be a
  benchmark case — grading a space on what you taught it measures nothing.
- **At least one negative case.** A question about data the space does not hold must be declined,
  not answered from a plausible-looking wrong table. An unanswerable question that returns a
  confident number is this system's most expensive failure mode, because nothing downstream
  flags it.
- **Grade on the answer, not on SQL text.** Two correct queries differ textually; assert on the
  result set or the value a caller would read.

**Before it serves real users, add:**

- Coverage of the shapes users actually ask: a filter, an aggregation, a group-by-and-rank, a
  period-over-period comparison, a multi-table join, and a question needing a business definition
  from `instructions.md`.
- An **expected answer with a source** per case — a validated query or known-good report. A case
  whose expected value nobody can source gets edited to match whatever the space returned.
- **Repeated runs, recorded as a pass rate.** One run of a non-deterministic system is not a
  result; a case that passes intermittently is failing.
- **The gate:** a change to `instructions.md`, `example_queries.yml`, `data_sources.yml`,
  `sql_functions.yml` or a backing view requires a fresh run before merge, and the pass rate must not
  fall below the `CHANGELOG.md` baseline. A deliberate drop records the new baseline and the
  reason in the same commit. A wording tidy needs no rerun.

---

## 12. Safety and data handling

- **Instructions are not an access control.** "Do not show salary data" is advisory to a model and
  bypassable by a rephrased question. If a column must not be readable, keep it out of
  `data_sources` — a UC grant, row filter or column mask on the underlying table, or a view that
  omits it (§5).
- **Text columns are untrusted input.** A document body or free-text field surfaced through a data
  source can contain instructions. `instructions.md` must state that column *content* is data to
  report, never an instruction to follow.
- **Be explicit about whose permissions apply.** Querying as the asking user or as the space's
  principal decides whether row-level security is real. Record which; never assume the narrower.
- **PII stays out unless the use case needs it.** Masking at the view is cheaper than a policy
  asking users not to ask.
- **Business definitions live in `instructions.md`, once.** "Active customer", "churn" — an
  unwritten definition is one the space invents per question, and two users get two numbers for
  the same word.
- State the refusal behaviour: what the space says when it cannot answer. An unstated refusal is
  improvised differently every time.

---

## Conformance

The audit checklist for this guideline lives beside it, in [`conformance/genie.md`](conformance/genie.md) — one file, one source of truth, loaded by whoever is auditing rather than by everyone who edits a file.
