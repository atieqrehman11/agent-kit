# API — conformance checklist

The audit list for [`api`](api.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing service.

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

Structure (from [`service-structure`](./service-structure.md)):

- [ ] Routers delegate to services; no business logic or data access in a router.
- [ ] All I/O — DB, object store, external HTTP, LLM — is behind a repository or client class.
- [ ] All models live under `schema/`.
- [ ] One exception hierarchy, one handler layer, one catch-all; no route builds an error body.
- [ ] Log level comes from configuration and defaults to `INFO`.
- [ ] No prompt, threshold, model id, URL or table name is a literal at a callsite.

If async jobs are supported:

- [ ] `POST /v1/jobs` returns `202`.
- [ ] `GET /v1/jobs/{job_id}` returns standard job state.
- [ ] Failed jobs use `state: "FAILED"` and include `error`.

If conversational access is needed:

- [ ] The use case API does not add chat endpoints by default.
- [ ] The use case API advertises `CONVERSATION_CONTEXT` only if it exposes context/actions for the conversational API.
- [ ] Chat endpoint and guardrail rules are handled by the [`chat-api`](./chat-api.md) guideline.

---
