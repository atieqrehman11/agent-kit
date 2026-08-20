# Databricks notebook source
# DBTITLE 1,Step 2 — Transform
# TPLVAR_DISPLAY_NAME — stage 2 of 2.
#
# In :  <catalog>.<schema>.TPLVAR_TABLE_PREFIXraw<table_suffix>
# Out:  <catalog>.<schema>.TPLVAR_TABLE_PREFIXcurated<table_suffix>
#
# Widgets mirror stage 1 — every stage declares the parameters it reads, so the
# values a run used are visible in the run itself rather than in a config file
# somewhere in the workspace.

dbutils.widgets.text("catalog", "TPLVAR_CATALOG")
dbutils.widgets.text("schema", "gold")
dbutils.widgets.text("table_suffix", "_v0")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
SUFFIX = dbutils.widgets.get("table_suffix")

SOURCE = f"{CATALOG}.{SCHEMA}.TPLVAR_TABLE_PREFIXraw{SUFFIX}"
TARGET = f"{CATALOG}.{SCHEMA}.TPLVAR_TABLE_PREFIXcurated{SUFFIX}"

# COMMAND ----------

# TODO: implement this stage. Same idempotency rule as stage 1.
raise NotImplementedError("task_02_transform: not implemented yet")
