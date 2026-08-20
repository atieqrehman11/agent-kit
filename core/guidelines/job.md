---
name: job
kind: guideline
description: >
  Standards for scheduled Databricks jobs: task structure, retries, alerting and
  idempotency. Applies when writing or reviewing a scheduled job.
applies_to:
  - "**/resources/*.job.yml"
  - "**/src/task_[0-9][0-9]_*.py"
  - "**/src/ddl/**"
---

# Job Standards — __ORG_PREFIX__Scheduled Databricks Job Reference

Best practices for the `job` repo type: a scheduled (or triggered) **Databricks Job**
(`resources.jobs`) that runs one task per stage from `src/task_0N_*.py`.

Implement domain logic in the `TODO` blocks of those stage files following the patterns
here.

---

## 1. When to use `job` (vs `etl`)

Choose `job` for batch or scheduled compute that is **not** a declarative transformation
graph:

- Orchestration / glue (call an API, move files, kick off downstream work).
- Batch exports (write a gold table out to a file, a downstream system, or a Volume).
- Model **batch** scoring or backfills.
- Scheduled maintenance (compaction, retention, table stats).

Choose `etl` instead when the work is a medallion pipeline of dependent tables — Auto
Loader → bronze → silver → gold with AI Functions. That belongs in a Lakeflow pipeline
(`resources.pipelines`), not a job. See [`pipeline`](./pipeline.md).

---

## 2. Canonical layout

```
databricks.yml               bundle name + uuid + dev/stg/prod targets + variables
resources/job.job.yml        the one job resource (schedule, tasks, task chain)
src/task_01_<verb>.py        one file per stage — implement the TODO blocks
src/task_02_<verb>.py
run_local.sh                 LOCAL dev deploy only (this laptop → dev workspace)
.gitlab-ci.yml               controller trigger (stg/prod)
run_resources.yml            empty — the job runs on its schedule, not on deploy
```

**One task per stage, chained with `depends_on`.** A failed run then resumes from the task
that failed rather than re-running everything before it, and the run page shows which stage
is slow. A single task doing five things is one opaque success-or-failure.

Name the files for what they do and number them for the order they run in — the numbering is
what makes the DAG legible next to the resource file that wires it.

---

## 3. Config: explicit parameters, not a config file

Every per-environment value is a **bundle variable** in `databricks.yml`, passed to each
task as a `base_parameters` entry and read by the stage as a widget:

```python
dbutils.widgets.text("catalog", "myapp_dev")
CATALOG = dbutils.widgets.get("catalog")
```

**Never hard-code a catalog, schema or workspace path in a stage file** — that is what makes
the same file run unchanged in dev, stg and prod.

Why parameters rather than a per-environment `task_config.yaml`: the values a run actually
used are then visible **in the run itself**, on the task's own page. With a config file you
are reading a file in the workspace and inferring which one the run picked up — and a
`config_dir` pointing at the wrong target is invisible until the output is wrong.

- Declare each parameter as a widget with a sensible dev default, so the notebook is also
  runnable interactively.
- Keep secrets out of parameters — read them from a Databricks secret scope at runtime.
- `config_dir` and `policy_id` stay **declared but unused** in `databricks.yml`: the CI/CD
  controller passes both on every deploy, and `bundle deploy` errors on an undeclared
  `--var`.

---

## 4. Scheduling

- `quartz_cron_expression` + `timezone_id` set the cadence; the scaffold defaults to daily
  07:00 America/Denver — adjust or remove.
- Ship with `pause_status: PAUSED` (and `trigger_pause_status: PAUSED` for stg) so a fresh
  deploy never starts firing before it is verified. Unpause deliberately.
- For file-driven work prefer a **file-arrival trigger** over a fixed cron.
- Jobs are **deploy-only** in CI: deploying registers the schedule; it does not run the job.
  `run_resources.yml` stays empty unless you explicitly want a run on every deploy.

---

## 5. Compute

**Default to serverless.** No `job_clusters` block, no `policy_id`, no cluster to size and
no start-up wait before the first stage runs. Most of these jobs are Delta reads and writes
plus some SQL or AI-function calls, which is exactly what serverless is for.

Reach for a **classic job cluster** only when serverless genuinely cannot do the work — a
pinned runtime version, an init script, a library the serverless environment will not
resolve, or a workload that needs specific instance types. Then:

- A **job cluster** (created per run, torn down after) — never an all-purpose cluster.
- `policy_id` (`${var.policy_id}`) becomes required: the run-as principal cannot create a
  cluster without a policy that permits it. Set the real id per environment.
- `data_security_mode: SINGLE_USER` for Unity Catalog access under the job's service
  principal.
- Right-size with `autoscale` (min/max workers). Start small.

Record *why* in a comment when you take the classic path. "It has always been a cluster" is
how a job keeps paying for a five-minute cold start it stopped needing two runtimes ago.

## 5a. Concurrency

- `max_concurrent_runs: 1` unless the job is genuinely safe to run twice at once. Two runs
  writing the same table is a corruption incident, not a throughput win.
- `queue.enabled: true` so a trigger that fires while the previous run is still going waits
  instead of being dropped.

---

## 6. Reliability

- **Idempotent by design.** A retried or re-run job must not double-write. Prefer
  `MERGE` / overwrite-by-partition over blind `append`; key writes on a natural id.
- Set task **retries** with backoff for transient failures; do not retry on validation
  errors.
- `email_notifications.on_failure` is wired to the team email — keep it current so failures
  are seen.
- Tag every run (`ci_commit_sha`, `environment`, `team`, `project`) so runs are traceable
  back to a commit.

---

## 7. Relationship to evaluation

If the job produces data or scores an agent/model consumes, scaffold `evaluation/` with
`{{cmd:eval:new}}` and point the spec at the gold table or endpoint the job feeds. Record
the eval baseline in the repo when the job's output logic changes materially.

---

## Conformance

The audit checklist for this guideline lives beside it, in [`conformance/job.md`](conformance/job.md) — one file, one source of truth, loaded by whoever is auditing rather than by everyone who edits a file.
