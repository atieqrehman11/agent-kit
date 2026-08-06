# Chat API — conformance checklist

The audit list for [`chat-api`](../chat-api.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing service.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `chat-api.md` — read it there when a check needs interpreting.

---

- [ ] `POST /v1/chat/message` exists.
- [ ] Successful responses use `text/event-stream`.
- [ ] Initial validation errors return JSON `ErrorResponse`.
- [ ] Stream emits `TOKEN` events.
- [ ] Successful stream ends with `DONE`.
- [ ] Failed stream ends with `ERROR`.
- [ ] Stream never emits `DONE` after `ERROR`.
- [ ] History is capped or validated.
- [ ] User-provided history is treated as untrusted input.
- [ ] Prompt injection checks run before model invocation.
- [ ] Tool/action execution is allowlisted.
- [ ] Caller authorization is enforced before using domain data or actions.
- [ ] Tool outputs are treated as untrusted model context.
- [ ] Logs redact secrets and sensitive content.
- [ ] OpenAPI documents the chat endpoint.
