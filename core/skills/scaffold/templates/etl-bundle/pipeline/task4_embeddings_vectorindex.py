# SKELETON — implement the TODO blocks.
# Task 4 — Embeddings & Vector Search Index
# Part A (pipeline): ai_query embedding model → gold.TPLVAR_RAW_PREFIX_chunks_with_embeddings
# Part B (run manually after pipeline): create/sync Vector Search index
# Input:   <catalog>.gold.TPLVAR_RAW_PREFIX_enriched_chunks
# Outputs: <catalog>.gold.TPLVAR_RAW_PREFIX_chunks_with_embeddings
#          <catalog>.gold.TPLVAR_RAW_PREFIX_chunks_index  (Vector Search)

# COMMAND ----------
from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, FloatType

# Per-environment values come from the pipeline's `configuration:` block
# (resources/etl.pipeline.yml), never from a literal here — a literal survives the
# target override untouched, so a stg run would read dev's data and succeed.
CATALOG      = spark.conf.get("pipeline.catalog")
SCHEMA       = spark.conf.get("pipeline.schema")
TABLE_PREFIX = spark.conf.get("pipeline.table_prefix")
GOLD_SCHEMA      = "gold"
EMBEDDING_MODEL  = "databricks-gte-large-en"  # 1024-dim, 512-token limit
VS_ENDPOINT_NAME = "TPLVAR_RAW_PREFIX-vs-endpoint"  # TODO: use a shared endpoint if one exists

_IN_ENRICHED    = GOLD_SCHEMA + "." + TABLE_PREFIX + "_enriched_chunks"
_OUT_EMBEDDINGS = GOLD_SCHEMA + "." + TABLE_PREFIX + "_chunks_with_embeddings"
VS_INDEX_NAME   = CATALOG + "." + GOLD_SCHEMA + "." + TABLE_PREFIX + "_chunks_index"
_SRC_TABLE      = CATALOG + "." + GOLD_SCHEMA + "." + TABLE_PREFIX + "_chunks_with_embeddings"

# COMMAND ----------
# Part A — TODO: implement and uncomment

# @dp.table(name=_OUT_EMBEDDINGS,
#           comment="Gold: enriched chunks with 1024-dim embedding vectors.",
#           table_properties={"quality": "gold", "delta.enableChangeDataFeed": "true"})
# def chunks_with_embeddings():
#     return (
#         spark.read.table(_IN_ENRICHED)
#         .withColumn(
#             "embedding",
#             F.expr("ai_query('" + EMBEDDING_MODEL + "', chunk_to_embed)")
#              .cast(ArrayType(FloatType()))
#         )
#         .withColumn("embedded_at", F.current_timestamp())
#     )

# COMMAND ----------
# Part B — run manually after the pipeline completes (not inside DLT)
# TODO: run this cell in a notebook or job after Part A succeeds

# from databricks.vector_search.client import VectorSearchClient
# client = VectorSearchClient()
#
# existing = [e["name"] for e in client.list_endpoints().get("endpoints", [])]
# if VS_ENDPOINT_NAME not in existing:
#     client.create_endpoint(name=VS_ENDPOINT_NAME, endpoint_type="STANDARD")
#     client.wait_for_endpoint(VS_ENDPOINT_NAME, timeout=600)
#
# indexes = [i["name"] for i in client.list_indexes(VS_ENDPOINT_NAME).get("vector_indexes", [])]
# if VS_INDEX_NAME not in indexes:
#     index = client.create_delta_sync_index(
#         endpoint_name                 = VS_ENDPOINT_NAME,
#         index_name                    = VS_INDEX_NAME,
#         source_table_name             = _SRC_TABLE,
#         pipeline_type                 = "TRIGGERED",
#         primary_key                   = "chunk_id",
#         embedding_vector_column       = "embedding",
#         embedding_dimension           = 1024,
#         embedding_model_endpoint_name = EMBEDDING_MODEL,
#         columns_to_sync = [
#             "chunk_id", "document_id", "document_type", "section_header",
#             "chunk_text", "chunk_label", "importance", "parent_chunk_text",
#         ],
#     )
#     index.wait_for_sync(timeout=1800)
# else:
#     index = client.get_index(VS_ENDPOINT_NAME, VS_INDEX_NAME)
#     index.sync()
#     index.wait_for_sync(timeout=1800)
