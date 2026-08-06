---
name: api
kind: guideline
description: >
  Standards every use-case API must meet: the required health and info endpoints, URL and
  naming rules, JSON and timestamp conventions, the error response shape, pagination, async
  jobs, security and observability, and the OpenAPI contract. Applies whenever a use-case
  API is designed, built or reviewed.
applies_to:
  - "**/routers/**/*.py"
  - "**/app.yml"
  - "**/docs/API_STANDARDS.md"
---

# Gen AI Platform API Standards
## Version 1.0

This document defines the minimum standard for building a new use case API.

Keep use case APIs focused on domain data, domain actions, reports, jobs, and files. Conversational/chat endpoints are not part of the default use case API surface. Chat is covered separately in the [`chat-api`](./chat-api.md) guideline.

This document is the **contract on the wire** — paths, payloads, status codes. How the service
behind that contract is arranged — routers delegating to services, services to repositories,
one exception hierarchy behind one handler, log levels from configuration, no hardcoded
prompts or thresholds — is [`service-structure`](./service-structure.md). Both apply to every
API; neither repeats the other.

---

## 1. What Every Use Case API Must Provide

Every conforming use case API must expose:

```text
GET /v1/health
GET /v1/info
```

Use case APIs may also expose:

```text
GET    /v1/{resources}
GET    /v1/{resources}/{resource_id}
POST   /v1/{resources}
PATCH  /v1/{resources}/{resource_id}
DELETE /v1/{resources}/{resource_id}
POST   /v1/jobs
GET    /v1/jobs/{job_id}
GET    /v1/{resources}/{resource_id}/download
```

Do not add `POST /v1/chat/message` to a normal use case API. If conversational access is needed, integrate with the dedicated conversational API.

---

## 2. How To Create A New Use Case API

Follow this sequence:

1. Start from a blank service or approved internal template.
2. Choose a stable, globally unique `service_id`, for example `agentic-kpi-reporting`.
3. Implement `GET /v1/health`.
4. Implement `GET /v1/info`.
5. Decide which optional capabilities the service supports.
6. Add domain endpoints using the URL and naming rules in this document.
7. Add shared error handling before frontend integration.
8. Add pagination for list endpoints.
9. Add async job endpoints if the service triggers long-running work.
10. Commit an OpenAPI 3.x spec with request and response schemas.
11. Run the conformance checklist.
12. Register the service `base_url` with the platform shell.

Optional capabilities:

| Capability | Meaning |
|---|---|
| `ASYNC_JOBS` | Service supports long-running job trigger and polling. |
| `REPORTING` | Service exposes report resources. |
| `FILE_DOWNLOADS` | Service exposes download endpoints. |
| `DASHBOARD_DATA` | Service exposes dashboard-ready data. |
| `CONVERSATION_CONTEXT` | Service exposes data/actions that the conversational API may call. |

`CHAT` is intentionally not listed as a normal use case capability. Chat belongs in the conversational API standard.

---

## 3. Service Identity

`GET /v1/info` returns metadata used by the platform shell.

Example response:

```json
{
  "service_id": "agentic-kpi-reporting",
  "display_name": "Agentic KPI Reporting",
  "description": "KPI reporting, anomaly summaries, and report generation.",
  "api_version": "v1",
  "service_version": "1.0.0",
  "status": "ACTIVE",
  "capabilities": ["ASYNC_JOBS", "REPORTING", "DASHBOARD_DATA", "CONVERSATION_CONTEXT"],
  "icon": "chart-line",
  "owner": "Analytics",
  "support_email": "support@example.com",
  "openapi_url": "/openapi.json"
}
```

Rules:

- `service_id` must be kebab-case and stable.
- `api_version` is the public API version, such as `v1`.
- `service_version` is the deployed implementation version, such as `1.0.0`.
- `status` must be one of `ACTIVE`, `INACTIVE`, or `MAINTENANCE`.
- `capabilities` must contain only supported use case capabilities from Section 2.

---

## 4. Health

`GET /v1/health` returns service readiness.

Example response:

```json
{
  "status": "OK",
  "service_id": "agentic-kpi-reporting",
  "api_version": "v1",
  "service_version": "1.0.0",
  "timestamp": "2026-06-12T14:30:00Z",
  "dependencies": {
    "delta_lake": "OK",
    "model_endpoint": "DEGRADED"
  }
}
```

Rules:

- `status` must be `OK`, `DEGRADED`, or `ERROR`.
- Return `200` when the service can handle normal traffic.
- Return `503` with `ErrorResponse` when a critical dependency is unavailable.
- Do not expose secrets, tokens, passwords, or connection strings.

---

## 5. URL And Naming Rules

Use this path shape:

```text
/{version}/{resources}
/{version}/{resources}/{resource_id}
/{version}/{resources}/{resource_id}/{sub-resource}
```

Good examples:

```text
GET  /v1/reports
GET  /v1/reports/{report_id}
GET  /v1/business-units/{business_unit_id}
POST /v1/jobs
GET  /v1/jobs/{job_id}
```

Rules:

- Use `/v1` as the version prefix.
- Use plural nouns for resources.
- Use lowercase hyphenated path segments.
- Use `snake_case` JSON fields and path parameter names.
- Do not use trailing slashes.
- Do not put API version in query parameters.
- Do not use generic `{id}`; use `{report_id}`, `{job_id}`, etc.
- `GET` requests must not have a body.

---

## 6. Request And Response Rules

Rules:

- JSON request and response bodies use `application/json`.
- JSON responses should be objects, not bare arrays.
- Timestamps must be UTC ISO-8601 strings ending in `Z`.
- Date-only fields use `YYYY-MM-DD`.
- Public platform-owned IDs should be UUID v4 strings.
- External IDs may keep their source format but must be clearly named, such as `external_run_id`.
- Enum values must be uppercase strings.
- Empty lists are `[]`, not `null`.
- Nullable fields should be documented in OpenAPI.
- Responses should include or propagate `X-Request-ID`.

Example timestamp:

```text
2026-06-12T14:30:00Z
```

---

## 7. Errors

All non-streaming errors must use this shape:

```json
{
  "error_code": "RESOURCE_NOT_FOUND",
  "message": "The requested report was not found.",
  "detail": null,
  "request_id": "4b485f87-3a77-4b4f-bd05-4cfbdb5b4e1c",
  "timestamp": "2026-06-12T14:30:00Z",
  "errors": null
}
```

Required fields:

- `error_code`
- `message`
- `request_id`
- `timestamp`

Common platform error codes:

| HTTP | error_code |
|---|---|
| `400` | `INVALID_REQUEST` |
| `401` | `UNAUTHENTICATED` |
| `403` | `FORBIDDEN` |
| `404` | `RESOURCE_NOT_FOUND` |
| `409` | `RESOURCE_CONFLICT` |
| `409` | `RESOURCE_NOT_READY` |
| `415` | `UNSUPPORTED_MEDIA_TYPE` |
| `422` | `VALIDATION_ERROR` |
| `429` | `RATE_LIMITED` |
| `500` | `INTERNAL_ERROR` |
| `502` | `UPSTREAM_BAD_RESPONSE` |
| `503` | `SERVICE_UNAVAILABLE` |
| `504` | `UPSTREAM_TIMEOUT` |

Rules:

- Never return `200` with an error payload.
- Never return `500` for caller-correctable validation errors.
- FastAPI default `{"detail": ...}` errors must be normalized to this shape.
- Service-specific error codes should be prefixed with the normalized service ID, for example `AGENTIC_KPI_REPORTING_REPORT_EXPIRED`.

---

## 8. Pagination

List endpoints that can return many records must use offset pagination.

Request parameters:

```text
limit=100
offset=0
```

Response shape:

```json
{
  "items": [],
  "limit": 100,
  "offset": 0,
  "total": 0,
  "has_more": false
}
```

Rules:

- Default `limit` is `100`.
- Maximum `limit` is `1000`.
- `offset` starts at `0`.
- Invalid pagination values return `400 INVALID_REQUEST`.

---

## 9. Async Jobs

Use async jobs for long-running operations such as report generation, file ingestion, model evaluation, and pipeline triggers.

If the service advertises `ASYNC_JOBS`, it must expose:

```text
POST /v1/jobs
GET  /v1/jobs/{job_id}
```

Trigger response:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_type": "GENERATE_REPORT",
  "state": "PENDING",
  "status_url": "/v1/jobs/550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-06-12T14:30:00Z",
  "message": "Report generation accepted.",
  "external_run_id": null
}
```

Job status response:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_type": "GENERATE_REPORT",
  "state": "RUNNING",
  "progress": {
    "completed": 2,
    "total": 5,
    "percent": 40
  },
  "created_at": "2026-06-12T14:30:00Z",
  "started_at": "2026-06-12T14:31:00Z",
  "completed_at": null,
  "result": null,
  "error": null,
  "external_run_id": "123456789"
}
```

Rules:

- Job trigger returns `202`.
- Job polling returns `200` for `PENDING`, `RUNNING`, `COMPLETE`, `FAILED`, and `CANCELLED`.
- A failed job is represented by `state: "FAILED"` plus `error`; it is not a polling endpoint `5xx`.
- Unknown `job_id` returns `404 RESOURCE_NOT_FOUND`.

---

## 10. Security And Observability

Production APIs must:

- Use HTTPS.
- Require platform-approved authentication.
- Enforce authorization for protected data and actions.
- Restrict CORS to approved frontend origins.
- Redact secrets from logs.
- Avoid returning secrets or connection details in responses.

Every request log should include:

- `timestamp`
- `service_id`
- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`
- `error_code` when applicable

Emit that line from **one middleware**, not from each route. Log levels themselves are
[`service-structure`](./service-structure.md) §4.

### Request identity

- Accept an inbound `X-Request-ID`; generate a UUID v4 when the caller does not send one.
- Echo it on **every** response, success and error alike, and put it in `ErrorResponse.request_id`.
- Propagate it to every downstream call so one id spans the whole request path.

### Limits and resilience

Defaults are configuration, never literals in code:

| Control | Rule |
|---|---|
| **Request timeout** | Every outbound call has an explicit connect and read timeout. No unbounded call. |
| **Retries** | Idempotent operations only, with capped exponential backoff and jitter. Never retry a `4xx` other than `429`. |
| **Rate limiting** | Public endpoints are rate limited; over-limit returns `429 RATE_LIMITED` with `Retry-After`. |
| **Payload size** | Cap request body and upload size; over-limit returns `413`. |
| **Pagination cap** | `limit` has a maximum; a larger value is clamped or rejected with `VALIDATION_ERROR` — never honoured. |
| **Concurrency** | Long-running work goes through `POST /v1/jobs` (§9), never a synchronous request held open. |

### Compatibility

- `/v1` is a contract. Within a version: add optional fields freely; **never** remove a field,
  rename one, tighten a type, or add a required request field.
- A breaking change is `/v2`, served alongside `/v1`.
- Deprecate before removing: mark it in OpenAPI, return the `Deprecation` header, and give
  consumers a stated window.

---

## 11. OpenAPI

Every service must commit an OpenAPI 3.x spec.

The spec must document:

- Endpoints
- Path parameters
- Query parameters
- Request schemas
- Response schemas
- Error responses
- Auth requirements
- Enum values
- Nullable fields

The OpenAPI spec is the contract. Frontend integration should start after the relevant OpenAPI changes are reviewed.

---

## 12. AI-Backed Endpoints

Rules for any endpoint whose response depends on a model call. **How the call itself is made —
prompt loading, redaction, retries, structured output, caching, logging and the eval gate — is
[`python-llm`](./python-llm.md).** This section is only what changes at the *API boundary*, where a
non-deterministic component sits behind a contract that must stay deterministic.

**The contract is stable even when the content is not.**

- The response schema is fixed and documented in OpenAPI like any other. Model free text goes in a
  **field**; it never becomes the shape of the response. An endpoint whose keys vary with what the
  model returned has no contract.
- Model output is validated against the response model before returning. A parse failure is a
  `502`-class dependency error, not a `200` carrying malformed content.
- **Never return the prompt, system instructions, or raw provider payloads.**

**The caller must be able to tell a grounded answer from a guess.**

- An answer derived from retrieved context carries its **sources** — document ids, table names or
  record keys. An answer with no verifiable provenance is a liability the caller cannot assess.
- **"Insufficient context" is a documented success state**, not an error and not a blank. An
  endpoint with no way to say "I could not ground this" fabricates instead.
- Expose a confidence or relevance score where one gated the answer; the threshold itself is
  configuration, per [`service-structure`](./service-structure.md).

**Model calls fail and cost money, so bound them at the boundary.**

- Every model call has an explicit timeout, shorter than the client's. Report the model endpoint's
  state in `GET /v1/health` — that is what `model_endpoint` in §4 is for.
- **Cap per request** from configuration: max input size, max output tokens, max model calls, max
  retrieval depth. An unbounded request is an unbounded bill.
- **Rate limit per client**, not just per service — one caller in a retry loop must not exhaust
  the provider quota for everyone.
- Generation that can exceed a few seconds uses the async job pattern in §9. Token streaming is
  conversational — see [`chat-api`](./chat-api.md).
- A retried `POST` must not re-spend: accept an idempotency key where the model call is expensive
  and return the stored result.
- Per-call logs are correlated by `request_id` and carry the **prompt version** — without it a
  latency or quality shift cannot be attributed to the change that caused it.

---

*API Standards v1.0 | Gen AI Platform*

---

## Conformance

The audit checklist for this guideline lives beside it, in [`conformance/api.md`](conformance/api.md) — one file, one source of truth, loaded by whoever is auditing rather than by everyone who edits a file.
