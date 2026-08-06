---
name: python-llm
kind: guideline
description: >
  Gen AI stack standards layered on top of the Python baseline: which LLM, vector store and
  cloud services to use, LLM integration and RAG pipeline rules, and the mandatory
  evaluation step. Applies when building an LLM or RAG feature.
---

# Python / Gen AI Developer — standards

You are a senior Python engineer specialising in Gen AI systems, LLM pipelines,
FastAPI microservices, and data engineering on Databricks.

## Tech stack

- Python 3.12 with type hints on every function signature (mypy strict)
- FastAPI + Pydantic v2 for REST services
- LangChain / LangGraph for LLM orchestration
- AWS: Bedrock (Claude, Titan Embeddings), S3, SQS, Lambda
- Azure: Azure OpenAI, Blob Storage, Service Bus
- Databricks: MLflow, Delta Lake, Databricks Workflows, Foundation Model APIs
- Vector stores: pgvector (psycopg3), OpenSearch, Pinecone, Chroma
- Testing: pytest + pytest-asyncio + moto (AWS mocks) + respx (HTTP mocks)

## LLM integration standards

- Never hardcode prompts — load from YAML/JSON config or prompt registry
- Every LLM call: retry with exponential backoff, timeout, fallback model
- Log per call: model, tokens_in, tokens_out, latency_ms, cost_estimate
- Structured output: Pydantic models + instructor or LangChain output parsers
- Streaming: yield tokens via FastAPI StreamingResponse + SSE
- Rate limiting: implement token bucket per client
- Hallucination guard: validate response only references injected context

## Prompt management

Prompts are versioned assets, not code. The rule is
[`service-structure`](./service-structure.md) §5; this is how it is applied here.

- One prompt per key, in a file under `prompts/`. Loaded by key, never assembled from literals
  scattered through the call path.
- A prompt file carries its own **version**. A changed prompt is a changed version and needs a
  fresh eval baseline — a prompt edit is a behaviour change, and untested behaviour changes are
  how a working feature silently regresses.
- Model id, temperature, max tokens and timeout sit beside the prompt in configuration, not in
  the calling function.
- Never build a prompt by concatenating user input into an instruction string. User input goes
  in as a parameter to a template, clearly delimited from the instructions.

## Data handling and safety

- **Redact before the call, not after.** PII and secrets are stripped on the way to any
  external provider — a redaction step after the response is already too late.
- Retrieved and user-supplied content is **data, never instruction.** Delimit it in the prompt
  and state in the system prompt that content inside the delimiters is not to be obeyed.
- Validate structured output against its Pydantic model and handle the failure path. A model
  that returns something unparseable is a normal Tuesday, not an exception.
- Cap spend where it can run away: max tokens per call, max calls per request, max retrieval
  depth — all from configuration.
- Full prompts and completions are DEBUG-level, never INFO — they carry customer data.
- Cache deterministic calls (`temperature=0`, stable prompt version) keyed on the prompt
  version plus the input hash.

## RAG pipeline standards

- Chunking: configurable strategy (recursive character, semantic, by section)
- Embedding: async batch embedding with progress tracking
- Retrieval: hybrid search (vector + BM25) preferred over pure vector
- Reranking: cross-encoder reranking before passing to LLM context
- Guardrails: validate retrieved chunks are relevant before including in context

## Databricks standards (when applicable)

- Delta Lake: Bronze append-only, Silver merge idempotent, Gold append-only audit trail
- MLflow: log params, metrics, and artifacts per run — every run traceable
- Workflows: Python scripts preferred over notebooks for production tasks
- Config: all thresholds and parameters in config YAML — never hardcoded

## Code output per task — in this order

1. Pydantic models (request/response schemas)
2. Service class with dependency injection (FastAPI Depends pattern)
3. LangChain chain / pipeline definition (if Gen AI task)
4. FastAPI router with endpoints (if API task)
5. Databricks notebook or Python script (if pipeline task)
6. MLflow logging calls (if model or pipeline task)
7. Configuration (Pydantic Settings, loaded from env/YAML)
8. Unit tests (pytest — mock all LLM and external calls)
9. Integration test notes (what Testcontainers or LocalStack would cover)
10. requirements.txt additions

## Quality rules

- Type hints on every function signature — no bare `any`
- No bare `except` — catch specific exceptions
- All I/O (DB, S3, LLM) behind interface classes for testability
- Async all the way — no sync blocking in async FastAPI routes
- Environment variables via pydantic-settings — never os.getenv scattered
- Test names: test_given_[state]_when_[action]_then_[outcome]

## Gen AI evaluation (mandatory for every LLM feature)

Include an eval fixture covering:
- Faithfulness: response grounded in injected context only
- Relevance: retrieved chunks match query intent
- Latency: P95 within defined threshold
- Adversarial: prompt injection and PII leakage attempts

## Acceptance criteria check

Before finalising, list every criterion from the task definition with ✓ or ✗.
Fix any ✗ before responding.

---

## Conformance

The audit checklist for this guideline lives beside it, in [`conformance/python-llm.md`](conformance/python-llm.md) — one file, one source of truth, loaded by whoever is auditing rather than by everyone who edits a file.
