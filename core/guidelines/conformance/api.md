# API — conformance checklist

The audit list for [`api`](../api.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing service.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `api.md` — read it there when a check needs interpreting.

---

Required:

- [ ] `GET /v1/health` exists.
- [ ] `GET /v1/info` exists.
- [ ] `service_id` is stable and kebab-case.
- [ ] Paths use `/v1`.
- [ ] Paths use lowercase hyphenated resource names.
- [ ] JSON fields use `snake_case`.
- [ ] Errors use `ErrorResponse`.
- [ ] FastAPI default errors are normalized.
- [ ] List endpoints use the pagination envelope, and `limit` has an enforced maximum.
- [ ] OpenAPI 3.x spec is committed.
- [ ] Production auth, authorization, CORS, and HTTPS are configured — CORS is an allowlist, never `*`.
- [ ] Logs include `service_id`, `request_id`, route, status, and latency, emitted from one middleware.
- [ ] `X-Request-ID` is accepted, generated when absent, and echoed on every response.
- [ ] Every outbound call has an explicit timeout; retries are capped and idempotent-only.
- [ ] Request body and upload size are capped.

Structure — layering, exceptions, logging and hardcoded values are
[`conformance/service-structure.md`](service-structure.md), which is always in scope when the
diff touches service code. Not restated here: a duplicated check is a finding reported twice.

If async jobs are supported:

- [ ] `POST /v1/jobs` returns `202`.
- [ ] `GET /v1/jobs/{job_id}` returns standard job state.
- [ ] Failed jobs use `state: "FAILED"` and include `error`.

If any endpoint's response depends on a model call:

- [ ] The response schema is fixed and documented in OpenAPI; model free text sits in a field and never determines the response shape.
- [ ] Model output is validated against the response model; a parse failure returns a dependency error, not a `200` with malformed content.
- [ ] No prompt, system instruction or raw provider payload is returned to the caller.
- [ ] Answers derived from retrieved context carry their sources — document ids, table names or record keys.
- [ ] "Insufficient context" is a documented success state with a reason, not a blank or an error.
- [ ] Every model call has an explicit timeout, shorter than the client's; `model_endpoint` state is reported in `GET /v1/health`.
- [ ] Max input size, max output tokens, max model calls and max retrieval depth are capped from configuration.
- [ ] Rate limiting is per client, not only per service.
- [ ] Generation that can exceed a few seconds uses the async job pattern in §9.
- [ ] Expensive model endpoints accept an idempotency key, so a retried `POST` does not re-spend.
- [ ] Per-call logs are correlated by `request_id` and carry the prompt version.

How the call itself is made — prompt loading, redaction, structured output, DEBUG-level prompt
logging and the eval gate — is [`conformance/python-llm.md`](python-llm.md).

If conversational access is needed:

- [ ] The use case API does not add chat endpoints by default.
- [ ] The use case API advertises `CONVERSATION_CONTEXT` only if it exposes context/actions for the conversational API.
- [ ] Chat endpoint and guardrail rules are handled by the [`chat-api`](../chat-api.md) guideline.

---
