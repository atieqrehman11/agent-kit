# SKELETON — implement the TODO blocks. See docs/PIPELINE_STANDARDS.md for guidance.
# Task 1 — Ingestion
# Pattern: Auto Loader (cloudFiles/binaryFile) → bronze table
# Input:   /Volumes/TPLVAR_CATALOG/bronze/unstructured_data/TPLVAR_SLUG/
# Output:  TPLVAR_CATALOG.bronze.TPLVAR_RAW_PREFIX_raw_documents

# COMMAND ----------
import os
from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG         = "TPLVAR_CATALOG"
TABLE_PREFIX    = "TPLVAR_RAW_PREFIX"
VOLUME_SCHEMA   = "bronze"
VOLUME_NAME     = "unstructured_data"
USE_CASE_FOLDER = "TPLVAR_SLUG"
FILE_GLOB       = "*"  # TODO: restrict to file types, e.g. "*.pdf"

_VOLUME_PATH = "/Volumes/" + CATALOG + "/" + VOLUME_SCHEMA + "/" + VOLUME_NAME + "/" + USE_CASE_FOLDER
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
