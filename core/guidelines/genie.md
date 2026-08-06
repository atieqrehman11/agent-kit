---
name: genie
kind: guideline
description: >
  Standards for Genie spaces: views, functions, instructions and benchmark coverage. Applies
  when building or reviewing a Genie space.
applies_to:
  - "**/genie-space/**"
  - "**/docs/GENIE_STANDARDS.md"
---

# Genie Standards — __ORG_PREFIX__Genie Space Reference

Standard for the `genie` repo type: a Databricks **Genie space** deployed via the Genie
**management API** (`createspace` / `updatespace`). There is no DAB bundle for Genie —
`src/deploy.py` assembles the payload from the repo files and calls the API.

The **repo is authoritative**: the space is (re)deployed *from* these files. All
answer-quality tuning (description, instructions, example queries, backing view) lives here.

---

## 1. Canonical layout

```
genie-space/
├── space.yml            the DEFINITION — title, warehouse_id, data_sources,
│                         sample_questions, + pointers to the prose / example files
├── description.md        the space Description as PROSE (pointed to by space.yml)
├── instructions.md       the space Instructions as PROSE (pointed to by space.yml)
├── example_queries.yml   OPTIONAL curated question -> SQL pairs (few-shot). Ships as a
│                         commented TEMPLATE with an empty list — nothing sent until filled
├── views/                EMPTY by default — add a bespoke backing-view .sql only if needed
└── functions/            EMPTY by default — UC-function DDL to attach to the space
CHANGELOG.md              version → date → eval baseline → what changed
src/validate.py           check space.yml — no credentials, no network
src/deploy.py             assemble serialized_space + reconcile via the API
deploy.sh                 local one-shot: pip install + apply DDL + deploy (dev)
.gitlab-ci.yml            two jobs, each one line: run validate.py, run deploy.py
GENIE_STANDARDS.md        this file
```

> **CI holds no logic of its own** — each stage runs one of these scripts, so every check
> that gates a deploy also runs on a laptop. `deploy.py` calls the same `validate.check()`
> before touching a workspace.

> **No dummy content is scaffolded.** `views/` and `functions/` start empty and
> `example_queries.yml` / `sample_questions` ship as commented templates. A Genie space
> points at *curated tables you already own*; you supply the data sources and examples.

---

## 2. Definition vs prose — keep them apart

**Structured wiring lives in `space.yml`; long text lives in the files it points to.**
The Genie Description and Instructions are multi-paragraph prose; inlining them as YAML
strings is painful to write and review, and a formatter can reflow them. So:

- `space.yml` holds machine-readable fields only: `title`, `warehouse_id`,
  `data_sources`, `sample_questions`, and the `*_file` pointers.
- `description.md`, `instructions.md`, and `example_queries.yml` hold the content.
  `src/deploy.py` reads them and folds them into the payload.

---

## 3. The `serialized_space` payload

`src/deploy.py` maps the repo files to the API's `serialized_space` (version 2):

| Payload field | Source | Notes |
|---|---|---|
| `title` | `space.yml: title` | |
| `description` | contents of `description.md` | verbatim |
| `instructions` | contents of `instructions.md` | verbatim |
| `data_sources` | `space.yml: data_sources` | tables + metric_views |
| `sample_questions` | `space.yml: sample_questions` | each gets a 32-char hex id |
| `example_queries` | `example_queries.yml` | **only if entries present** — see §6 |

The example-queries field name is a **Public-Preview API detail** — confirm it for your
workspace version and adjust the mapping in `src/deploy.py` if it differs.

---

## 4. Identity and environments — declare, don't record

**The repo stores no id for the deployed space.** `space.yml` declares what should exist; it
does not record what does. Identity is two axes together:

| Axis | Source |
|---|---|
| Which workspace | `DATABRICKS_HOST` / the CLI profile the deploy authenticated with |
| Which space in it | the title `"<title> [ENV]"`, from config + `--env` |

`src/deploy.py` lists the workspace's spaces and matches that title: one match → **update**;
none → **create**; more than one → **fail**. Every environment is suffixed, prod included —
one rule, no exception, so the title is derivable from `(config, env)` alone in CI as on a
laptop.

**Why not store the id?** CI cannot hold it. A runner checks out fresh, reads an empty id,
creates a *new* space, and discards the write-back — one more per pipeline run. A field per
environment does not help: the id is an output of a deploy, and CI's only place to put an
output is a commit, which is a race.

Two consequences:

- **`title` is the identity.** Renaming it does not rename the deployed space; the next
  deploy creates a new one under the new title. Clean up the old one yourself.
- **Duplicate titles are a hard error** — deploy refuses rather than silently retargeting
  someone else's resource.

Same model as a DAB target: declarative identity plus a per-target workspace, no deploy state
in git. `agent` repos follow it by supervisor name; see `AGENT_STANDARDS.md`.

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
- `src/deploy.py` reads the file via `space.yml: example_queries_file` and includes any
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
7. **Check it** — `python src/validate.py`. Same check CI runs first and `deploy.py` runs
   before touching a workspace; it needs no credentials.
8. **Deploy** — `./deploy.sh` locally (dev), or merge to `stg` / `prod` for CI.

---

## 9. Deployment

| Target | How |
|---|---|
| **local (dev)** | `./deploy.sh` — pip install, apply DDL, then reconcile the space |
| **stg / prod** | merge to the `stg` / `prod` branch — CI runs `src/deploy.py --env <branch>` |

Auth uses the default Databricks SDK chain (`DATABRICKS_HOST` + token, or a CLI profile)
plus a `warehouse_id` in `space.yml`. For stg / prod those two variables are set **per
branch** in GitLab CI/CD settings — the workspace they point at is what separates the
environments, since the repo stores no per-environment id (§4).

> The Genie management API is **Public Preview**. Confirm the `serialized_space` field names
> for your workspace version before the first deploy.
> See https://docs.databricks.com/api/workspace/genie/createspace

---

## 10. Versioning & the eval loop

- Keep `CHANGELOG.md`: version → date → eval baseline → what changed, one row per deploy.
- The loop: **edit `genie-space/` → deploy → run `evaluation/` → record the baseline**.
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
- **The gate:** a change to `instructions.md`, `description.md`, `example_queries.yml`,
  `data_sources` or a backing view requires a fresh run before merge, and the pass rate must not
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
