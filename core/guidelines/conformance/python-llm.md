# Python / Gen AI — conformance checklist

The audit list for [`python-llm`](../python-llm.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing LLM or RAG feature.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `python-llm.md` — read it there when a check needs interpreting.

**This sheet audits the model call**, and nothing another sheet already covers. Deliberately not here, so no check is reported twice:

| Also in scope | Sheet |
|---|---|
| Complexity, single responsibility, tests for new logic, test naming | [`python`](python.md) |
| Layering, no-literal-prompt, DEBUG-level prompt logging, config validation | [`service-structure`](service-structure.md) |
| The endpoint exposing the call, per-client rate limiting | [`api`](api.md) |

If the LLM call is **not** in service code — a pipeline or notebook — `service-structure` is out of scope, so check its prompt-literal and DEBUG-logging items here instead.

Skip any section with no matching surface in the diff; never flag its absence.

---

Prompt management:

- [ ] Every prompt is one file under `prompts/`, loaded **by key**, never assembled from literals scattered through the call path.
- [ ] Each prompt file carries its own **version**.
- [ ] Model id, temperature, max tokens and timeout sit beside the prompt in configuration, not in the calling function.
- [ ] User input enters as a **parameter to a template**, clearly delimited — never concatenated into an instruction string.

Every LLM call:

- [ ] Has an explicit timeout.
- [ ] Has retry with exponential backoff.
- [ ] Has a defined fallback model, or a documented decision not to.
- [ ] Logs model, `tokens_in`, `tokens_out`, `latency_ms` and `cost_estimate`.
- [ ] Sits behind a repository or client class, not called inline from business logic.

Structured output:

- [ ] Responses are parsed into Pydantic models via instructor or a LangChain output parser.
- [ ] Output is validated against its model and the **failure path is handled** — an unparseable response is a normal case, not an exception.
- [ ] A grounding check exists: the response references only the injected context.

Data handling and safety:

- [ ] **Redaction happens before the call**, not after — PII and secrets are stripped on the way to any external provider.
- [ ] Retrieved and user-supplied content is delimited in the prompt, and the system prompt states that content inside the delimiters is not to be obeyed.
- [ ] Spend caps come from configuration: max tokens per call, max calls per request, max retrieval depth.
- [ ] Deterministic calls (`temperature=0`, stable prompt version) are cached, keyed on prompt version plus input hash.

RAG pipeline (if the feature retrieves):

- [ ] The chunking strategy is configurable, not hardcoded.
- [ ] Embedding is async and batched, with progress tracking.
- [ ] Retrieval is hybrid (vector + BM25) rather than pure vector, or the choice is justified.
- [ ] Cross-encoder reranking runs before chunks reach the LLM context.
- [ ] Retrieved chunks are validated for relevance before being included in context.

Quality rules:

- [ ] Type hints on every signature — no bare `any`.
- [ ] No bare `except`; specific exceptions only.
- [ ] All I/O — DB, object store, LLM — sits behind an interface class for testability.
- [ ] Async all the way; no sync blocking inside an async FastAPI route.
- [ ] Configuration via pydantic-settings, not `os.getenv` scattered through the code.
- [ ] Tests mock **all** LLM and external calls; no test reaches a live provider.

Databricks (when applicable):

- [ ] Delta write mode matches the layer: Bronze append-only, Silver merge idempotent, Gold append-only audit trail.
- [ ] MLflow logs params, metrics and artifacts per run, so every run is traceable.
- [ ] Production tasks are Python scripts rather than notebooks.
- [ ] All thresholds and parameters live in config YAML.

Evaluation — mandatory for every LLM feature:

- [ ] An eval fixture exists.
- [ ] **Faithfulness** is covered: the response is grounded in injected context only.
- [ ] **Relevance** is covered: retrieved chunks match query intent.
- [ ] **Latency** is covered: P95 within a defined threshold.
- [ ] **Adversarial** is covered: prompt injection **and** PII leakage attempts.
- [ ] A prompt version, model id or threshold change triggered a fresh eval run before merge, with scores at or above the previous baseline.

---
