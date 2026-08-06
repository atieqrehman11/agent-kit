# Service Structure — conformance checklist

The audit list for [`service-structure`](service-structure.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing service.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `service-structure.md` — read it there when a check needs interpreting.

---

Layering:

- [ ] Boundary contains no business logic, no data access and no LLM calls.
- [ ] Services contain no HTTP types, status codes or framework request/response objects.
- [ ] All I/O — including LLM and external HTTP calls — is behind a repository or client class.
- [ ] No layer is skipped, and no cycle exists between layers.
- [ ] The transaction boundary is the service method.

Placement:

- [ ] All models live under `schema/` (or the language's equivalent), defined once.
- [ ] Every file's directory matches its layer.

Failure:

- [ ] All domain exceptions descend from one base and carry a stable `error_code`.
- [ ] No framework or HTTP exception is raised below the boundary.
- [ ] Exactly one handler layer produces error responses; no route builds one by hand.
- [ ] A catch-all handler exists, logs at ERROR with a stack trace, and leaks nothing internal.
- [ ] No broad `except`/`catch` outside the catch-all.
- [ ] Retries, timeouts and backoff live in the repository layer.

Logging:

- [ ] Logging is configured once at startup and nowhere else.
- [ ] The level comes from configuration, defaults to `INFO`, and DEBUG needs no code change.
- [ ] Log lines are structured and carry a correlation id.
- [ ] Prompts, payloads and parameter values are at DEBUG, not INFO.
- [ ] No secrets or PII in logs at any level.
- [ ] No `print()` in service code.

Configuration:

- [ ] No prompt or instruction text is a string literal in source.
- [ ] No model id, temperature, threshold, limit, URL, bucket or table name is a literal at a callsite.
- [ ] Configuration is validated at startup and fails loudly on a missing key.
- [ ] No secret is present in source or in committed configuration.
