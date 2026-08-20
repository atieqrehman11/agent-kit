# Genie — conformance checklist

The audit list for [`genie`](../genie.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing Genie space.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `genie.md` — read it there when a check needs interpreting.

**The prose is the product here.** A diff touching only `instructions.md` or `example_queries.yml` is a behaviour change to a non-deterministic system, and the benchmark section below is the part that must not be skipped for it. Skip any section with no matching surface in the diff; never flag its absence.

---

Layout and separation:

- [ ] `space.yml` holds the instruction id and nothing else — no prose inlined as YAML strings, and no manifest re-listing the files that are found by convention.
- [ ] The instruction id is committed. It is what makes a redeploy edit the instructions in place instead of dropping them and adding a copy.
- [ ] The prose is `src/instructions.md`, read by name and sent byte-verbatim; `title` and `description` are DAB fields in `resources/genie.yml`, not payload.
- [ ] `src/views/` and `src/functions/` contain only what the space actually needs — no view added for its own sake.
- [ ] `python/validate.py` passes, and needs no credentials or network to run.

Identity:

- [ ] The repo stores **no space id** — DAB owns identity through the resource key in `resources/genie.yml`.
- [ ] Every environment is title-suffixed, prod included, set per target in `databricks.yml`.
- [ ] The resource key has not been renamed: renaming destroys and recreates the space, losing its id and every conversation in it.
- [ ] `generated/space.<target>.json` is committed and current for **every** environment — the controller clones fresh and runs no project scripts, so a stale artifact deploys green.
- [ ] Every identifier starts with `${catalog}.${schema}.`; no deployed file names a literal catalog.

Data sources:

- [ ] Data sources point at curated tables — gold layer or a purpose-built view. **Never raw or bronze.**
- [ ] Any bespoke view is re-appliable `CREATE OR REPLACE VIEW` DDL under `src/views/`, exposing exactly the columns Genie should query with names it can reason about.
- [ ] UC functions are `CREATE OR REPLACE FUNCTION` DDL under `src/functions/` and listed in `src/sql_functions.yml`.
- [ ] DDL is applied to the catalog before the space is deployed, by hand or by a stage of the job repo that owns the tables it reads — the bundle deploys no DDL, and a space whose functions do not exist deploys clean and answers nothing.
- [ ] Where a declared function's DDL lives in another repo, that repo is named in `sql_functions.yml` — the create API does not validate functions the way it validates tables, so nothing else records the dependency.

Answer quality:

- [ ] Every example query runs and returns the right answer, pasted from a validated source.
- [ ] Example queries reference only tables listed in `data_sources`.
- [ ] There are 5–15 high-quality question → SQL pairs rather than many weak ones.
- [ ] `sample_questions` are real, answerable questions — not placeholders.
- [ ] Every business term a question depends on is defined once in `instructions.md`.
- [ ] `instructions.md` states the grounding rule and what the space says when it cannot answer.

Benchmark coverage — the accuracy gate:

- [ ] A benchmark set exists, and it is **held out**: no question is used both as an example query and as a benchmark case.
- [ ] Coverage includes a simple filter, an aggregation, a group-by-and-rank, a period-over-period comparison, a multi-table join, and a question needing a business definition.
- [ ] Negative cases are covered — a question about data the space does not hold is **declined**, not answered from a plausible wrong table.
- [ ] Grading asserts on the returned answer or result set, not on SQL string similarity.
- [ ] Every case records its expected answer and the validated source that expected answer came from.
- [ ] The set was run repeatedly and a pass rate recorded — not graded on a single run.
- [ ] A change to `instructions.md`, `example_queries.yml`, `data_sources.yml`, `sql_functions.yml` or a backing view triggered a fresh run before merge.
- [ ] The recorded pass rate is **at or above** the `CHANGELOG.md` baseline; any drop is recorded as a deliberate trade with its reason in the same commit.
- [ ] `docs/CHANGELOG.md` has a row for this deploy: version → date → eval baseline → what changed.

Safety and data handling:

- [ ] `instructions.md` states that text-column **content** is data to report, never an instruction to follow.
- [ ] No column that must not be readable is reachable through `data_sources` — restriction is by UC grant, row filter, column mask or an omitting view, **not** by an instruction asking the model not to show it.
- [ ] Whose permissions apply — the asking user or the space principal — is recorded, and row-level security is not assumed.
- [ ] PII exposed through the space is masked at the view unless the use case requires it.

---
