# Databricks notebook source
# DBTITLE 1,Step 1 — Ingest
# TPLVAR_DISPLAY_NAME — stage 1 of 2.
#
# In :  TODO — the source this stage reads
# Out:  <catalog>.<schema>.TPLVAR_TABLE_PREFIXraw<table_suffix>
#
# Every per-environment value arrives as a widget, set from base_parameters in
# resources/job.job.yml. Nothing here names a catalog, a schema or a workspace —
# that is what makes the same file run in dev, stg and prod.

dbutils.widgets.text("catalog", "TPLVAR_CATALOG")
dbutils.widgets.text("schema", "gold")
dbutils.widgets.text("table_suffix", "_v0")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
SUFFIX = dbutils.widgets.get("table_suffix")

TARGET = f"{CATALOG}.{SCHEMA}.TPLVAR_TABLE_PREFIXraw{SUFFIX}"

# COMMAND ----------

# TODO: implement this stage.
#
# Write idempotently — the job is configured to resume from a failed task, so a
# re-run of this stage must produce the same table rather than appending a second
# copy. A MERGE on a natural key, or an overwrite of a partition, both qualify.
#
# Fails loudly on purpose: an empty stub that "succeeded" reports a green run for
# work that never happened, and the next stage reads nothing.
raise NotImplementedError("task_01_ingest: not implemented yet")
