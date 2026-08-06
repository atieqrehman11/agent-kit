# Job — conformance checklist

The audit list for [`job`](../job.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing scheduled job.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `job.md` — read it there when a check needs interpreting.

Job code is Python, so [`python`](python.md) applies too — complexity limits, single responsibility, and tests for new logic. Skip any section below with no matching surface in the diff; never flag its absence.

---

Repo type is the right one:

- [ ] The work is orchestration, batch export, batch scoring, backfill or maintenance — not a medallion graph of dependent tables.
- [ ] If it is a medallion pipeline, it belongs in `resources.pipelines` and follows [`pipeline`](../pipeline.md) instead.

Configuration:

- [ ] No catalog, environment name or other environment-specific value is hardcoded in `src/main.py`.
- [ ] Per-environment values live in `config/DEV|STG|PROD/task_config.yaml`, resolved via `${var.config_dir}`.
- [ ] `main.py` loads the config passed by `--config` and fails loudly on a missing required key.
- [ ] No secret is in a config file; secrets are read from a Databricks secret scope at runtime.

Idempotency and reliability:

- [ ] A retried or re-run job cannot double-write — writes use `MERGE` or overwrite-by-partition, keyed on a natural id, rather than blind `append`.
- [ ] Task retries are configured with backoff for transient failures.
- [ ] Retries do **not** fire on validation errors.
- [ ] `email_notifications.on_failure` is set to a current team address.
- [ ] Runs are tagged with `ci_commit_sha`, `environment`, `team` and `project`, so a run traces back to a commit.

Scheduling:

- [ ] `quartz_cron_expression` and `timezone_id` are set deliberately, not left at the scaffold default.
- [ ] The job ships `pause_status: PAUSED` (and `trigger_pause_status: PAUSED` for stg) so a fresh deploy does not start firing before it is verified.
- [ ] File-driven work uses a file-arrival trigger rather than a fixed cron.
- [ ] `run_resources.yml` is empty unless a run on every deploy is explicitly wanted.

Compute:

- [ ] The job uses a **job cluster**, not an all-purpose cluster.
- [ ] `policy_id` is set to the real policy for the target environment.
- [ ] `data_security_mode: SINGLE_USER` is set for Unity Catalog access under the job's service principal.
- [ ] The cluster is right-sized with `autoscale` min/max workers rather than a large fixed size.

Evaluation:

- [ ] If the job produces data or scores consumed by an agent or model, an `evaluation/` area exists and its spec points at the gold table or endpoint the job feeds.
- [ ] A material change to output logic records a fresh eval baseline in the repo.

---
