# Job — conformance checklist

The audit list for [`job`](../job.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing scheduled job.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `job.md` — read it there when a check needs interpreting.

Job code is Python, so [`python`](python.md) applies too — complexity limits, single responsibility, and tests for new logic. Skip any section below with no matching surface in the diff; never flag its absence.

---

Repo type is the right one:

- [ ] The work is orchestration, batch export, batch scoring, backfill or maintenance — not a medallion graph of dependent tables.
- [ ] If it is a medallion pipeline, it belongs in `resources.pipelines` and follows [`pipeline`](../pipeline.md) instead.

Configuration:

- [ ] No catalog, schema, volume path or other environment-specific value is hardcoded in a stage file.
- [ ] Per-environment values are bundle variables in `databricks.yml`, overridden per target, and reach each task as `base_parameters`.
- [ ] Each stage declares the parameters it reads as widgets, with a dev default, so it is also runnable interactively.
- [ ] `config_dir` and `policy_id` are declared in `databricks.yml` even when unused — the controller passes both and `bundle deploy` errors on an undeclared `--var`.
- [ ] No secret is passed as a parameter; secrets are read from a Databricks secret scope at runtime.

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

- [ ] Compute is **serverless** unless a stated reason requires otherwise, recorded in a comment.
- [ ] If classic compute is used: a **job cluster**, never an all-purpose cluster, and `policy_id` set to the real policy for the target environment.
- [ ] `data_security_mode: SINGLE_USER` is set for Unity Catalog access under the job's service principal.
- [ ] If classic compute is used: the cluster is right-sized with `autoscale` min/max workers rather than a large fixed size.
- [ ] `max_concurrent_runs: 1` unless the job is genuinely safe to run concurrently, and `queue.enabled: true` so a trigger during a run waits rather than being dropped.
- [ ] One task per stage, chained with `depends_on`, so a failed run resumes rather than re-running everything.

Evaluation:

- [ ] If the job produces data or scores consumed by an agent or model, an `evaluation/` area exists and its spec points at the gold table or endpoint the job feeds.
- [ ] A material change to output logic records a fresh eval baseline in the repo.

---
