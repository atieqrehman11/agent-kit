---
name: pipeline
kind: guideline
description: >
  Standards for Lakeflow / ETL pipelines: medallion layering, table and checkpoint
  conventions, and quality expectations. Applies when writing or reviewing a pipeline.
---

# Pipeline Standards — __ORG_PREFIX__Lakeflow Reference

Best practices, AI Function guidance, and fallback options for the 4-task
Lakeflow pipeline pattern used across all repos.

Implement domain logic in the `TODO` blocks of each task notebook following
the patterns described here.

---

## Task 1 — Ingestion

**Goal:** Stream source files from a Unity Catalog Volume into a bronze Delta table.

- Use `cloudFiles.format = "binaryFile"` — works for all file types (PDF, DOCX, CSV, JSON, etc.).
- Set `cloudFiles.includeExistingFiles = "true"` on the first run to backfill existing files.
- Derive `document_id` from the **relative** file path (strip the volume prefix, remove the extension, replace `/` with `__`). Absolute paths break when the volume is remounted.
- Store raw bytes + metadata only — no parsing here. One row per file.

---

## Task 2 — Parse & Extract

**Goal:** Parse raw bytes into structured text and extract typed metadata fields.

- `ai_parse_document(content, map('version', '2.0'))` returns a VARIANT with `text`, `sections`, and page metadata. Store the full VARIANT — don't extract only the text.
- `ai_extract(parsed:text, schema)` takes a JSON Schema string. Define only the fields you will query — fewer fields = faster extraction and lower cost.
- Write a separate typed `_document_summary` table (one row per document) as the NL-to-SQL target. Keep the VARIANT in `_parsed_documents` for the chunking stage.

**Fallback (if `ai_extract` is unavailable in your region):**
```python
F.expr(f"ai_query('{LLM}', concat('Extract as JSON matching this schema: {SCHEMA}\n\n', parsed:text))")
```
Parse the returned JSON string with `from_json()`.

---

## Task 3 — Chunk & Classify

**Goal:** Split documents into embedding-ready chunks; classify and score each chunk.

- `ai_prep_search(parsed)` produces section-aware chunks with `chunk_text`, `chunk_to_embed`, `section_header`, `page_numbers`, and `token_count`. Prefer it over manual character/sentence splitting.
- Filter chunks with `token_count > 500` — the embedding model (`databricks-gte-large-en`) has a 512-token limit.
- Build **parent chunks** (full section text grouped by `section_header`) alongside child chunks. The retriever can then return broader context when a single chunk is too narrow.
- **Contextual retrieval:** prefix `chunk_to_embed` with the document summary before embedding. The model sees document-level context for every chunk, improving retrieval relevance significantly.
- Enable `delta.enableChangeDataFeed = true` on the output table — required for Vector Search Delta Sync.

**Fallback (if `ai_prep_search` is unavailable):**
Split `parsed:text` manually using sentence boundaries or fixed character windows, generate `chunk_id` with `md5(concat(document_id, chunk_index))`.

**Fallback (if `ai_classify` is unavailable):**
```python
F.expr(f"ai_query('{LLM}', concat('Classify into one of {LABELS}: ', chunk_text))")
```
Parse the single-word response.

---

## Task 4 — Embeddings & Vector Search Index

**Goal:** Generate embedding vectors and build a Delta Sync Vector Search index.

**Part A (pipeline task):**
- Use `databricks-gte-large-en` — 1024-dim vectors, 512-token limit.
- `ai_query(model, chunk_to_embed)` returns the embedding as a string; cast to `ArrayType(FloatType())`.
- Enable `delta.enableChangeDataFeed = true` — required for Delta Sync.

**Part B (standalone Workflow notebook task — runs after Part A):**
- Run Part B as a separate Workflow notebook task, not inside the Lakeflow pipeline. It uses the Vector Search SDK, not the pipeline runtime.
- Use `pipeline_type = "TRIGGERED"` for scheduled/batch workloads. Use `"CONTINUOUS"` only if near-real-time retrieval is a hard requirement.
- `columns_to_sync` controls what is returned in search results and what is available for metadata filtering. Include every field the retriever or the UI needs.

**Part C (smoke test):**
- Always run a smoke test after the index syncs. Use `query_type = "HYBRID"` — it combines ANN (vector similarity) and BM25 (keyword). Better recall than ANN alone for keyword-heavy queries.

---

## AI Functions — Regional Availability

| Function | Status | Notes |
|---|---|---|
| `ai_parse_document` | GA | Available in all regions |
| `ai_query` | GA | Available in all regions |
| `ai_extract` | Public Preview | Regionally limited — test first |
| `ai_classify` | Public Preview | Regionally limited — test first |
| `ai_prep_search` | Beta | Regionally limited — test first |

Verify availability before building the pipeline:

```sql
SELECT ai_classify('test', array('a', 'b'));
SELECT ai_extract('test', '{"type":"object","properties":{"title":{"type":"string"}}}');
SELECT ai_prep_search(ai_parse_document(content, map('version', '2.0')))
  FROM (SELECT content FROM <catalog>.raw.<volume> LIMIT 1);
```

---

## Scheduling

- Schedule the Lakeflow pipeline nightly or trigger on file arrival (Volume File Arrival trigger).
- New files dropped in the Volume are auto-detected by Auto Loader on the next run.
- Subsequent pipeline runs skip unchanged inputs — only new or modified files flow through.
- The Vector Search sync (Part B) updates only new or changed chunks.

---

## Unity Catalog naming convention

| Object | Pattern |
|---|---|
| Catalog | Use case catalog or `rapid_prototype_dev` for dev |
| Source volume | `<catalog>.raw.<volume-name>` |
| Pipeline schema | `<catalog>.pipeline` |
| Tables | `<catalog>.pipeline.<TABLE_PREFIX>_<stage>` |
| VS index | `<catalog>.pipeline.<TABLE_PREFIX>_chunks_index` |

`TABLE_PREFIX` is set per use case (e.g. `aeo_disc`) to avoid naming collisions when multiple use cases share the same catalog.
