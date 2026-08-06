---
name: chat-api
kind: guideline
description: >
  The contract for a dedicated conversational API: the service boundary between it and the
  use case APIs it orchestrates, the streaming request/response shape over Server-Sent
  Events, the guardrail layer that must run before model invocation and before any tool
  call, tool allowlisting, and the chat error codes. Applies whenever a chat, streaming or
  conversational endpoint is designed, built or reviewed. Domain endpoints follow the `api`
  guideline instead — see its service-boundary section.
applies_to:
  - "**/routers/**/chat*.py"
  - "**/chat/**/*.py"
  - "**/docs/CHAT_API_STANDARDS.md"
---

# Chat API Standards

This document defines the standard for the dedicated conversational API.

Normal use case APIs should not implement chat endpoints. They should expose domain data and actions. The conversational API owns chat, prompt handling, model routing, history policy, guardrails, and tool/action orchestration.

---

## 1. Service Boundary

The conversational API owns:

- Chat request and streaming response contract
- System prompts and developer instructions
- Model routing and model configuration
- Prompt injection handling
- Content safety checks
- Tool/action allowlists
- Conversation history policy
- Retrieval/context assembly
- Audit logging for conversational interactions
- Rate limits for conversational workloads

Use case APIs own:

- Domain resources and actions
- Domain authorization
- Domain validation
- Domain-specific error codes
- Reports, async jobs, files, and dashboard data
- Optional context endpoints used by the conversational API

Use case APIs that are safe for chat orchestration may advertise:

```text
CONVERSATION_CONTEXT
```

This does not require the use case API to expose a chat endpoint.

---

## 2. Required Endpoint

The conversational API must expose:

```text
POST /v1/chat/message
```

This endpoint streams Server-Sent Events over an HTTP `POST` response.

Browser clients should consume it with `fetch` streaming, not native `EventSource`, because `EventSource` does not support `POST` request bodies.

---

## 3. Request

Example request:

```json
{
  "message": "Why did throughput drop yesterday?",
  "history": [
    {
      "role": "USER",
      "content": "Show me yesterday's summary."
    },
    {
      "role": "ASSISTANT",
      "content": "Throughput declined by 4.2% compared with the previous day."
    }
  ],
  "context": {
    "service_id": "example-reporting-service",
    "report_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

Rules:

- `message` is required.
- `history` is required and may be empty.
- `history.role` must be `USER` or `ASSISTANT`.
- `history` should be capped at 10 turns.
- `context` is optional and service-defined.
- `message`, `history`, and `context` must be treated as untrusted input.
- User-provided history must not be treated as system or developer instructions.

---

## 4. Streaming Response

Successful response headers:

```text
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Request-ID: <request-id>
```

Initial request validation errors must return normal JSON `ErrorResponse`, not an SSE stream.

Every SSE frame uses:

```text
data: {json}

```

Token event:

```text
data: {"type":"TOKEN","content":"Throughput dropped"}

```

Done event:

```text
data: {"type":"DONE","message_id":"550e8400-e29b-41d4-a716-446655440000","prompt_tokens":120,"completion_tokens":340}

```

Error event:

```text
data: {"type":"ERROR","error_code":"CONVERSATION_MODEL_TIMEOUT","message":"Model endpoint timed out","request_id":"4b485f87-3a77-4b4f-bd05-4cfbdb5b4e1c"}

```

Rules:

- The stream should begin within 3 seconds after request acceptance.
- `TOKEN` events may contain one token, multiple tokens, words, or text chunks.
- Clients append `TOKEN.content` in received order.
- `DONE` is the final event on success.
- `ERROR` is the final event on failure.
- A stream must not emit `DONE` after `ERROR`.
- The service may send heartbeat comments to keep the connection alive.

---

## 5. Guardrails

The conversational API must enforce a shared guardrail layer before model invocation and before tool/action execution.

At minimum, guardrails must address:

- Prompt injection in `message`, `history`, retrieved context, and tool outputs
- Data exfiltration attempts
- Unauthorized action attempts
- Unsafe or unsupported tool calls
- Sensitive data leakage
- Excessive prompt or history size
- Model timeout and retry behavior

Rules:

- Do not execute arbitrary client-supplied tool names, URLs, SQL, Python, or code.
- Tool/action execution must be allowlisted.
- Tool/action execution must map to approved use case API endpoints.
- The conversational API must enforce the caller's authorization before using domain data or actions.
- Logs must not include secrets or sensitive prompt content unless approved by policy.

---

## 6. Tool And Use Case API Integration

When the conversational API calls a use case API:

- Use the use case API's documented OpenAPI contract.
- Propagate `X-Request-ID`.
- Propagate caller identity or authorization context when required.
- Respect use case API authorization decisions.
- Treat tool responses as untrusted model context.
- Normalize tool failures into conversational errors.

Use case APIs should expose clear, narrow endpoints for conversational use instead of requiring the conversational API to call broad internal endpoints.

---

## 7. Chat Error Codes

Common chat-level error codes:

| HTTP/SSE | error_code |
|---|---|
| `400` | `INVALID_REQUEST` |
| `401` | `UNAUTHENTICATED` |
| `403` | `FORBIDDEN` |
| `422` | `VALIDATION_ERROR` |
| `429` | `RATE_LIMITED` |
| SSE | `CONVERSATION_MODEL_TIMEOUT` |
| SSE | `CONVERSATION_GUARDRAIL_BLOCKED` |
| SSE | `CONVERSATION_TOOL_FAILED` |
| `500` | `INTERNAL_ERROR` |
| `503` | `SERVICE_UNAVAILABLE` |

Initial request errors use the main API `ErrorResponse` shape defined in the [`api`](./api.md) guideline. Mid-stream failures use the SSE `ERROR` event.

---

## Conformance

The audit checklist for this guideline lives beside it, in [`conformance/chat-api.md`](conformance/chat-api.md) — one file, one source of truth, loaded by whoever is auditing rather than by everyone who edits a file.
