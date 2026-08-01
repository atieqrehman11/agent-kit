# SKELETON — implement the TODO blocks. See docs/PIPELINE_STANDARDS.md for guidance.
# Task 3 — Chunk & Classify
# Pattern: ai_prep_search → chunks; ai_classify + ai_query → labels & importance
# Inputs:  TPLVAR_CATALOG.silver.TPLVAR_RAW_PREFIX_parsed_documents
#          TPLVAR_CATALOG.silver.TPLVAR_RAW_PREFIX_document_summary
# Output:  TPLVAR_CATALOG.gold.TPLVAR_RAW_PREFIX_enriched_chunks  (Change Data Feed enabled)

# COMMAND ----------
from pyspark import pipelines as dp
from pyspark.sql import functions as F, Window

CATALOG       = "TPLVAR_CATALOG"
TABLE_PREFIX  = "TPLVAR_RAW_PREFIX"
SILVER_SCHEMA = "silver"
GOLD_SCHEMA   = "gold"
LLM           = "databricks-claude-sonnet-4-6"

_IN_PARSED  = SILVER_SCHEMA + "." + TABLE_PREFIX + "_parsed_documents"
_IN_SUMMARY = SILVER_SCHEMA + "." + TABLE_PREFIX + "_document_summary"
_OUT_CHUNKS = GOLD_SCHEMA + "." + TABLE_PREFIX + "_enriched_chunks"

# TODO: set labels for your domain
CHUNK_LABELS = ["category_a", "category_b", "other"]

# TODO: update prompt for your domain (model must reply with one word: low/medium/high)
IMPORTANCE_PROMPT = "Rate importance for [your use case]. Reply: low, medium, or high. Excerpt: "

# COMMAND ----------
# TODO: implement and uncomment

# @dp.table(name=_OUT_CHUNKS,
#           comment="Gold: section-aware chunks with classification and importance.",
#           table_properties={"quality": "gold", "delta.enableChangeDataFeed": "true"})
# def enriched_chunks():
#     parsed  = spark.read.table(_IN_PARSED)
#     summary = spark.read.table(_IN_SUMMARY)
#
#     label_expr = "array(" + ", ".join("'" + l + "'" for l in CHUNK_LABELS) + ")"
#     win = Window.partitionBy("document_id", "section_header").rowsBetween(
#         Window.unboundedPreceding, Window.unboundedFollowing
#     )
#
#     chunked = (
#         parsed
#         .select("document_id", F.expr("ai_prep_search(parsed)").alias("prep"))
#         .select("document_id", F.explode("prep.chunks").alias("chunk"))
#         .select(
#             "document_id",
#             F.col("chunk.chunk_id").alias("chunk_id"),
#             F.col("chunk.chunk_text").alias("chunk_text"),
#             F.col("chunk.chunk_to_embed").alias("chunk_to_embed"),
#             F.col("chunk.section_header").alias("section_header"),
#             F.col("chunk.token_count").alias("token_count"),
#         )
#         .filter(F.col("token_count") <= 500)
#         .withColumn("parent_chunk_id",
#             F.md5(F.concat_ws("__", F.col("document_id"), F.col("section_header"))))
#         .withColumn("parent_chunk_text",
#             F.concat_ws("\n\n", F.collect_list("chunk_text").over(win)))
#         .withColumn("chunk_label", F.expr("ai_classify(chunk_text, " + label_expr + ")"))
#         .withColumn("importance",
#             F.lower(F.trim(F.expr("ai_query('" + LLM + "', concat('" + IMPORTANCE_PROMPT + "', chunk_text))"))))
#     )
#
#     chunked = chunked.join(
#         summary.select("document_id", "doc_summary", "document_type"),
#         on="document_id", how="left",
#     )
#
#     return chunked.withColumn(
#         "chunk_to_embed",
#         F.when(F.col("doc_summary").isNotNull(),
#             F.concat(F.lit("Summary: "), F.col("doc_summary"), F.lit("\n\n"), F.col("chunk_to_embed"))
#         ).otherwise(F.col("chunk_to_embed"))
#     )
