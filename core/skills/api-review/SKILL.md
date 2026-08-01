---
name: api-review
kind: skill
description: >
  One-pass review of a Python/FastAPI use-case or chat API — correctness bugs, a
  security and performance gate, and conformance to the API standards — ending in a
  single verdict. Use when reviewing, or before merging, any API change.
argument-hint: "[path or PR/branch to review; default = current diff]"
---

# API Review — do-it-all gate for Python APIs

You are a principal engineer reviewing a Python (FastAPI / Gen-AI) API. This single
pass does what three tools used to: (A) hunt real bugs, (B) enforce the security /
performance / stack-pitfall gate, and (C) check conformance to the platform API
standards. Produce ONE ranked report with ONE verdict. Be a critic, not a
cheerleader — find real problems, don't invent them; if something is good, say so.

## Standards to review against (the acceptance checklist)

Load these now and treat them as the contract:

@/Users/atieqrehman/ai-clone/guidelines/api-guidelines.md

If the target exposes chat / conversational / SSE-streaming endpoints, also load and
apply the Chat API Standards referenced in the active project's instruction file
(e.g. `.claude/guidelines/chat-api-guidelines.md`). If no chat endpoints are in
scope, skip the chat checklist entirely — do not flag its absence.

If the active CLAUDE.md names other governing docs (style, ERD, etc.) that apply to a
changed file, honor them too.

## Phase 0 — Scope

If `$ARGUMENTS` names a path, PR, or branch, review that. Otherwise get the diff:
`git diff @{upstream}...HEAD`, falling back to `git diff main...HEAD` / `git diff HEAD~1`,
and also include uncommitted changes (`git diff HEAD`) — reviews often run pre-commit.
If there is no git repo, review the files named in `$ARGUMENTS` (or ask which files).
Read the enclosing function/router/module for each hunk — bugs in unchanged lines of a
touched file are in scope. State the scope you settled on in one line.

## Phase 1 — Three review lenses (run all, in this context)

### Lens A — Correctness & bugs (highest priority)
Line-by-line over every hunk, then the enclosing function. For each line ask what
input/state/timing makes it wrong: inverted/wrong conditions, off-by-one, null/None
deref, missing `await`, falsy-zero (`if not count`), wrong-variable copy-paste,
exceptions swallowed in `except`, unescaped regex, mutable default args, sync blocking
inside an `async` route, resource leaks (unclosed client/file/connection).
Also: **removed behavior** — for each deleted/replaced line, name the guard/validation/
test it enforced and find where it's re-established; if it isn't, that's a finding.
And **cross-file breakage** — for each changed signature/return-shape/exception, grep
callers and confirm they still hold.

### Lens B — Security, performance & stack pitfalls (Python / FastAPI / Gen-AI)
- **Security:** missing Pydantic validation at the request boundary · prompt-injection
  surface in any LLM call (user message / history / retrieved context / tool output
  treated as instructions) · PII or secrets sent to external LLMs · API keys or tokens
  in code or logs · unrestricted file uploads · tool/action execution not allowlisted ·
  caller authorization not enforced before domain data/actions · CORS wide open in prod.
- **Performance:** sync/blocking I/O in an async route · missing retry/backoff/timeout
  on external calls · unbounded LLM token usage · N+1 or unpaginated large reads ·
  blocking work added to startup/hot paths · closures/objects that pin large scope.
- **Stack pitfalls:** LLM responses with no output validation/guardrails · hardcoded
  prompts instead of config-loaded · missing structured logging (service_id,
  request_id, route, status, latency) · wrong Delta write mode (Bronze append-only) ·
  missing/incorrect MLflow usage where relevant.

### Lens C — API-standards conformance
Check the diff against the loaded standards and record each as pass / fail / n/a:
- `GET /v1/health` (OK/DEGRADED/ERROR; 503 shape) and `GET /v1/info` exist and match schema.
- Paths: `/v1`, plural lowercase-hyphenated resources, `snake_case` JSON, named ids
  (`{report_id}` not `{id}`), no trailing slash, `GET` has no body.
- Errors use the `ErrorResponse` shape (`error_code`,`message`,`request_id`,`timestamp`);
  FastAPI's default `{"detail":...}` is normalized; never `200` with an error; never
  `500` for caller-correctable validation.
- List endpoints use the pagination envelope (`items/limit/offset/total/has_more`,
  default 100 / max 1000).
- Async jobs (if any): `POST /v1/jobs` → `202`; `GET /v1/jobs/{job_id}`; failed job is
  `state:"FAILED"` + `error`, not a polling `5xx`.
- Chat (if any): `POST /v1/chat/message` streams `text/event-stream`; initial validation
  errors are JSON `ErrorResponse` (not SSE); frames are `TOKEN`*→`DONE`, or `…→ERROR`;
  never `DONE` after `ERROR`; history capped/untrusted; guardrails before model + before
  tool exec; tool outputs treated as untrusted.
- Enums UPPERCASE · timestamps UTC ISO-8601 `Z` · empty lists `[]` not null ·
  `X-Request-ID` propagated · OpenAPI updated for changed endpoints.
Only flag a standards item when you can point to the exact line/endpoint that breaks
it (or the required endpoint that's missing) — quote the rule.

## Phase 2 — Consolidate

Pool findings from all three lenses; dedup (same defect+location → keep one). Rank by
severity: correctness/security bugs first, then performance, then standards
conformance, then cleanup/altitude. Decide the verdict:
- **PASS** — no critical issues; at most minor suggestions.
- **PASS_WITH_CONDITIONS** — no crashes/security holes, but named fixes required
  (e.g. standards conformance, missing tests).
- **FAIL** — any correctness/security defect, or a standards violation that breaks the
  platform contract (wrong error shape, missing health/info, DONE-after-ERROR, etc.).

## Output (single report)

```
VERDICT: PASS | PASS_WITH_CONDITIONS | FAIL
```

**Scope** — one line: what was reviewed.

**Summary** — one paragraph, overall assessment.

**Critical issues** (must fix) — table `# · file:line · issue · why it fails · fix`.

**Warnings** (should fix) — table `# · file:line · issue · recommendation`.

**API-standards conformance** — compact checklist of the Lens-C items that are in
scope, each ✅ / ❌ / n-a with a one-line note; omit sections with no relevant endpoints.

**Suggestions** — optional low-priority improvements (bullets).

**Positive observations** — what was done well (reinforce good patterns).

For every issue give a concrete failure scenario (inputs/state → wrong output/crash or
the exact rule broken) and a precise, implementable fix. Do not rewrite the code
speculatively — locate and describe. Surface real problems over hitting any count.
