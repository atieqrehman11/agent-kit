# SKELETON — implement the TODO blocks.
# Task 1 — Ingestion
# Pattern: Auto Loader (cloudFiles/binaryFile) → bronze table
# Input:   the pipeline's source_volume
# Output:  <catalog>.bronze.TPLVAR_RAW_PREFIX_raw_documents

# COMMAND ----------
import os
from pyspark import pipelines as dp
from pyspark.sql import functions as F

# Per-environment values come from the pipeline's `configuration:` block
# (resources/etl.pipeline.yml), never from a literal here — a literal survives the
# target override untouched, so a stg run would read dev's data and succeed.
CATALOG      = spark.conf.get("pipeline.catalog")
SCHEMA       = spark.conf.get("pipeline.schema")
TABLE_PREFIX = spark.conf.get("pipeline.table_prefix")
FILE_GLOB    = "*"  # TODO: restrict to file types, e.g. "*.pdf"

# The source volume is a whole path, not a name assembled from parts — a cleansed
# or refined input often does not live under <catalog>/bronze at all.
_VOLUME_PATH = spark.conf.get("pipeline.source_volume")
_OUT_TABLE   = TABLE_PREFIX + "_raw_documents"

os.makedirs(_VOLUME_PATH, exist_ok=True)

# COMMAND ----------
# TODO: implement and uncomment

# @dp.table(
#     name             = _OUT_TABLE,
#     comment          = "Bronze: raw files ingested via Auto Loader.",
#     table_properties = {"quality": "bronze"},
# )
# def raw_documents():
#     return (
#         spark.readStream
#             .format("cloudFiles")
#             .option("cloudFiles.format", "binaryFile")
#             .option("pathGlobFilter", FILE_GLOB)
#             .option("cloudFiles.includeExistingFiles", "true")
#             .load(_VOLUME_PATH)
#             .select(
#                 F.regexp_replace(
#                     F.regexp_replace(F.col("path"), r"^.*/" + USE_CASE_FOLDER + "/", ""),
#                     r"\.[^.]+$", ""
#                 ).alias("document_id"),
#                 F.col("content"),
#                 F.col("path").alias("source_path"),
#                 F.col("_metadata.file_modification_time").alias("ingested_at"),
#             )
#     )
