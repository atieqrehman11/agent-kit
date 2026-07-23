# SKELETON — implement the TODO blocks. See docs/PIPELINE_STANDARDS.md for guidance.
# Task 2 — Parse & Extract
# Pattern: ai_parse_document → VARIANT; ai_extract → typed metadata table
# Input:   TPLVAR_CATALOG.bronze.TPLVAR_RAW_PREFIX_raw_documents  (same pipeline)
# Outputs: TPLVAR_CATALOG.silver.TPLVAR_RAW_PREFIX_parsed_documents
#          TPLVAR_CATALOG.silver.TPLVAR_RAW_PREFIX_document_summary  (NL-to-SQL target)

# COMMAND ----------
from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, DateType

CATALOG       = "TPLVAR_CATALOG"
TABLE_PREFIX  = "TPLVAR_RAW_PREFIX"
SILVER_SCHEMA = "silver"
LLM           = "databricks-claude-sonnet-4-6"

_IN_RAW      = TABLE_PREFIX + "_raw_documents"
_OUT_PARSED  = SILVER_SCHEMA + "." + TABLE_PREFIX + "_parsed_documents"
_OUT_SUMMARY = SILVER_SCHEMA + "." + TABLE_PREFIX + "_document_summary"

# TODO: update to match your domain
EXTRACTION_SCHEMA = """
{
  "type": "object",
  "properties": {
    "document_type": {"type": "string"},
    "title":         {"type": "string"},
    "effective_date":{"type": "string"},
    "doc_summary":   {"type": "string"}
  }
}
"""

# COMMAND ----------
# TODO: implement and uncomment

# @dp.table(name=_OUT_PARSED, comment="Silver: parsed document VARIANT + extracted metadata.",
#           table_properties={"quality": "silver"})
# def parsed_documents():
#     raw = spark.read.table(_IN_RAW)
#     return (
#         raw
#         .withColumn("parsed",    F.expr("ai_parse_document(content, map('version', '2.0'))"))
#         .withColumn("extracted", F.expr("ai_extract(parsed:text, '" + EXTRACTION_SCHEMA + "'::STRING)"))
#         .drop("content")
#     )

# @dp.table(name=_OUT_SUMMARY, comment="Silver: typed document metadata, one row per document.",
#           table_properties={"quality": "silver"})
# def document_summary():
#     return (
#         spark.read.table(_OUT_PARSED)
#         .select(
#             "document_id", "source_path", "ingested_at",
#             F.col("extracted:document_type").cast(StringType()).alias("document_type"),
#             F.col("extracted:title").cast(StringType()).alias("title"),
#             F.col("extracted:effective_date").cast(DateType()).alias("effective_date"),
#             F.col("extracted:doc_summary").cast(StringType()).alias("doc_summary"),
#         )
#     )
