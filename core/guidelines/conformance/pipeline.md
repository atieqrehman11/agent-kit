# Pipeline — conformance checklist

The audit list for [`pipeline`](../pipeline.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing pipeline.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `pipeline.md` — read it there when a check needs interpreting.

Pipeline code is Python, so [`python`](python.md) applies too — complexity limits, single responsibility, and tests for new transformation logic. Skip any section below with no matching surface in the diff; never flag its absence.

---

Medallion layering and write semantics:

- [ ] Bronze is append-only and immutable — nothing rewrites or cleans in bronze.
- [ ] Silver merges idempotently on a natural key, so a replayed batch converges instead of duplicating.
- [ ] Gold is derived and rebuildable from silver.
- [ ] The write mode is correct for the layer — no blind `append` where a `MERGE` is required.
- [ ] Reprocessing a single document is possible without a full rebuild, keyed on `document_id`.

Data quality:

- [ ] **Every** table declares expectations, not only the last one.
- [ ] Each expectation drops or quarantines on violation, and which was chosen is recorded with the reason.
- [ ] Every table carries lineage columns — source path, ingest timestamp, pipeline run id.
- [ ] Schema evolution is additive; a type change or dropped column is versioned as a new table.

Ingestion (task 1):

- [ ] Auto Loader uses `cloudFiles.format = "binaryFile"`.
- [ ] `document_id` derives from the **relative** file path, not an absolute one.
- [ ] Bronze stores raw bytes plus metadata only — no parsing at this stage, one row per file.

Parse and extract (task 2):

- [ ] The full VARIANT from `ai_parse_document` is stored, not only the extracted text.
- [ ] The `ai_extract` schema defines only fields that are actually queried.
- [ ] A typed one-row-per-document summary table exists as the NL-to-SQL target.

Chunk and classify (task 3):

- [ ] Chunks over the embedding model's token limit are filtered out.
- [ ] Parent chunks are built alongside child chunks.
- [ ] `chunk_to_embed` is prefixed with document context before embedding.
- [ ] `delta.enableChangeDataFeed = true` is set on tables feeding Vector Search.

Embeddings and index (task 4):

- [ ] Embedding dimensions and token limit match the chosen model.
- [ ] Part B runs as a separate Workflow notebook task, not inside the Lakeflow pipeline.
- [ ] `pipeline_type` is `TRIGGERED` unless near-real-time retrieval is a stated hard requirement.
- [ ] `columns_to_sync` includes every field the retriever or UI needs for filtering and display.
- [ ] A smoke test runs after the index syncs, using `query_type = "HYBRID"`.

AI Functions:

- [ ] Every Public Preview or Beta function used was verified available in the target region.
- [ ] A documented fallback exists for each preview function the pipeline depends on.
- [ ] AI Function output is **persisted**, not recomputed per read.
- [ ] The prompt or schema string that produced AI output is versioned, so a re-extraction is explainable.

Security and PII:

- [ ] PII is classified and handled at the point it enters silver — masked, tokenised, or grant-restricted.
- [ ] No unclassified column is sent to a model by an AI Function.
- [ ] No secret appears in pipeline source or committed configuration.

Naming and scheduling:

- [ ] Tables follow `<catalog>.pipeline.<TABLE_PREFIX>_<stage>`; `TABLE_PREFIX` is set per use case.
- [ ] The source volume follows `<catalog>.raw.<volume-name>`; the index follows `<TABLE_PREFIX>_chunks_index`.
- [ ] Unity Catalog access uses the three-level `catalog.schema.table` namespace.
- [ ] The schedule is a nightly cron or a Volume file-arrival trigger, chosen deliberately.

---
