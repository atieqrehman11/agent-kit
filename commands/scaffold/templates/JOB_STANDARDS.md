# Job Standards — __ORG_PREFIX__Scheduled Databricks Job Reference

Best practices for the `job` repo type: a scheduled (or triggered) **Databricks Job**
(`resources.jobs`) that runs plain PySpark from `src/main.py`.

Implement domain logic in the `TODO` blocks of `src/main.py` following the patterns here.

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
(`resources.pipelines`), not a job. See `PIPELINE_STANDARDS.md`.

---

## 2. Canonical layout

```
databricks.yml               bundle name + uuid + dev/stg/prod targets + variables
resources/job.job.yml        the one job resource (schedule, clusters, tasks)
src/main.py                  entry point: run(config) — implement the TODO blocks
config/DEV|STG|PROD/         per-environment task_config.yaml (catalog, params)
bundle.sh                    LOCAL dev deploy only (this laptop → dev workspace)
.gitlab-ci.yml               enterprise controller trigger (stg/prod)
team_config.yaml             controller registration (bundle_name, uuid, url)
run_resources.yml            empty by default — the job runs on its schedule, not on deploy
```

---

## 3. Config: one file per environment

The job reads `${var.config_dir}/task_config.yaml`, and `config_dir` resolves to
`config/DEV`, `config/STG`, or `config/PROD` per target. **Never hard-code the catalog or
environment-specific values in `src/main.py`** — put them in the per-env config so the same
code runs unchanged in dev, stg, and prod.

- Keep secrets out of config files — read them from a Databricks secret scope at runtime.
- The `--config` path is passed by the job task; `main.py` should load it and fail loudly
  if a required key is missing.

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

## 5. Clusters & policy

- Use a **job cluster** (created per run, torn down after) — not an all-purpose cluster.
- `policy_id` (`${var.policy_id}`) is required so the run-as principal is allowed to create
  the cluster; set the real policy id per environment in `databricks.yml`.
- `data_security_mode: SINGLE_USER` for Unity Catalog access under the job's service
  principal.
- Right-size with `autoscale` (min/max workers). Start small; a batch job rarely needs a
  large fixed cluster.

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
`/usecase-eval:new` and point the spec at the gold table or endpoint the job feeds. Record
the eval baseline in the repo when the job's output logic changes materially.
