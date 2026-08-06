---
name: service-structure
kind: guideline
description: >
  How a service is put together, independent of language: the boundary → service → repository
  layer chain and what each layer may not do, where models and config live on disk, one typed
  exception hierarchy behind one boundary handler, log levels driven by configuration rather
  than code, and the rule that no prompt, threshold, endpoint or model parameter is a literal
  at a callsite. Applies whenever service code is written, restructured or reviewed.
applies_to:
  # Deliberately not "**/schema/**": adding a field to a model does not need the
  # layering, exception and logging rules, and a glob that fires on every model
  # edit is one that gets tuned out. §2's placement rule still arrives via these.
  - "**/routers/**"
  - "**/services/**"
  - "**/repositories/**"
  - "**/controller/**"
  - "**/service/**"
  - "**/repository/**"
---

# Service Structure — __ORG_PREFIX__shared standard, all languages

The **shape** layer. Pair it with the language standard (`python` / `java` / `react`), which
covers how to write the code, and with the resource standard (`api` / `pipeline` / `job` /
`agent`), which covers what the resource must expose. This document covers only how the
pieces are arranged, and it says the same thing in every language.

Five rules. Each one exists because its absence is expensive to undo later, not because it
is tidy.

## Applies to

Any service with a request boundary — an HTTP API, a message consumer, an agent supervisor,
a scheduled job with a task entry point. A notebook exploring data is exempt; a notebook
promoted to a production task is not.

---

## 1. The layer chain

```
boundary  ──▶  service  ──▶  repository  ──▶  the outside world
(router)       (logic)       (all I/O)         db · object store · HTTP · LLM provider
```

| Layer | Owns | May **not** |
|---|---|---|
| **Boundary** | Parse, validate, authenticate/authorise, delegate, serialise the response | Business logic, data access, LLM calls, transaction control, hand-built error bodies |
| **Service** | All business logic and orchestration; owns the transaction | Know anything about HTTP — no status codes, no request/response objects, no headers |
| **Repository** | All I/O, one concern per class: timeouts, retries, backoff, connection handling | Business logic, or calling a service |

Rules:

- **Calls go one direction only.** A repository never calls a service; a service never
  imports the boundary layer. A cycle between layers is a defect, not a style preference.
- **Never skip a layer**, even when the middle one is a pass-through today. A router that
  reaches a repository directly is the change that makes the next change hard — the
  pass-through costs six lines and is where the first business rule will land.
- **The transaction boundary is the service method.** Not the router, not the repository.
- **DTOs do not cross into the domain.** The boundary maps request → domain input and domain
  result → response. Persistence models do not leave the repository.

Per-stack naming — the chain is the same, the words differ:

| | Boundary | Service | Repository |
|---|---|---|---|
| Python / FastAPI | `routers/` — `APIRouter` | `services/` — plain classes, injected via `Depends` | `repositories/` — DB, object store, HTTP and LLM clients |
| Java / Spring Boot | `@RestController` | `@Service` behind an interface | `@Repository` / port + adapter |
| Agent supervisor | tool entry point | supervisor logic | tool implementation |

---

## 2. Where things live

Models live under `schema/`, in one place, so there is one answer to "what shape is this".

Python:

```
src/
  routers/         boundary — one module per resource
  services/        business logic — one module per use case
  repositories/    all I/O — db, object store, external HTTP, LLM clients
  schema/          all models: request, response, domain, config — Pydantic
  core/            config loading, logging setup, exception types, handlers, dependencies
  prompts/         prompt and instruction files, versioned (§5)
  utils/           genuinely shared helpers
tests/
```

Java (the Maven multi-module layout in the `java` standard):

```
api/             controllers + DTOs
domain/          domain model, service interfaces, ports, domain exceptions
infrastructure/  adapters, repository implementations, external clients
application/     configuration properties, wiring, exception handlers
```

Rules:

- **One model per concept, defined once, under `schema/`.** A request model redefined inline
  in a router is a second source of truth for the same contract.
- Separate the request/response models from the persistence model when they diverge. Do not
  separate them speculatively when they do not.
- A file's directory states its layer. A service class in `routers/` is misfiled even if it
  is correct.

---

## 3. Failure — typed exceptions, one handler

**Domain code raises. The boundary translates. Nothing in between builds an error body.**

- Every domain exception descends from **one base exception** for the service, and carries a
  stable `error_code`, a caller-safe `message`, and optional structured `detail`.
- **Never raise a framework or HTTP exception below the boundary.** A service that raises
  `HTTPException` has taken a dependency on being called over HTTP, and cannot be reused by
  a job, a consumer or an agent tool.
- **Exactly one handler layer at the boundary** maps exception → the standard error response
  (shape defined by the `api` standard). One registered handler per exception family, plus
  one catch-all. No route builds an error response by hand.
- **The catch-all is mandatory.** Any unmapped exception becomes `500 INTERNAL_ERROR`, logged
  at ERROR with the stack trace and the `request_id`, and returns nothing internal to the
  caller — no stack trace, no SQL, no upstream URL, no prompt.
- **Catching to add context and re-raising is correct; catching to continue is not.** Inside
  a service, catch a narrow exception, log with context, re-raise as a domain exception that
  names what failed. Never `except Exception` / `catch (Exception)` outside the catch-all.
- **Retries, timeouts and backoff on external calls live in the repository**, and a repository
  raises a domain exception when it gives up — never a raw client error.

Maintain the mapping as **one table in the service** — exception → `error_code` → status —
not as scattered `if` statements. The `error_code` and status values themselves are not
defined here: they come from the [`api`](./api.md) standard's error table, which is the single
source for them. An unmapped exception is `500 INTERNAL_ERROR`.

---

## 4. Logging — level comes from configuration

**Logging is configured once, at startup, from configuration. Never in module code.**

- One logging setup function, called once during startup. No `basicConfig`, no `setLevel`,
  no handler attached anywhere else in the codebase.
- **The level is read from configuration** — `LOG_LEVEL` env var or the config file —
  defaulting to `INFO`. Turning on DEBUG in an environment must require **a configuration
  change and a restart, and no code change and no new build**. If someone has to edit a
  source file to see debug output, this rule is not met.
- Every log line is **structured** (key/value or JSON) and carries the correlation id —
  `request_id`, job run id, or conversation id — so one unit of work can be reconstructed.

What belongs at each level:

| Level | Content |
|---|---|
| `ERROR` | Unhandled failures and the catch-all. Always with a stack trace. |
| `WARNING` | Degraded but handled — a retry, a fallback, an upstream timeout that recovered. |
| `INFO` | Lifecycle and one line per unit of work: started, finished, outcome, duration, counts. Safe to leave on in production. |
| `DEBUG` | Diagnostic detail: payload shapes, resolved prompts, retrieved chunks, generated SQL, parameter values. Off in production by default. |

Rules:

- **Never log secrets, tokens, credentials or PII at any level.** Redact at the point of
  logging, not by hoping DEBUG stays off.
- Full prompts and model inputs are DEBUG, never INFO — they carry customer data.
- **No `print()` in service code.** (The `python` standard's allowance for `print()` covers
  notebook and job driver output only, and does not extend to a service.)
- Log once per failure. A line at the repository, another at the service and a third at the
  handler is one incident reported three times.

---

## 5. No hardcoded values

**A literal appears once, at its definition. A literal at a callsite is the defect.**

| Category | Examples | Home |
|---|---|---|
| **Prompts & instructions** | system prompts, tool descriptions, few-shot examples, refusal and fallback text | versioned files under `prompts/`, one prompt per key, loaded by key |
| **Model & inference params** | model id, temperature, max tokens, top_p, timeout | configuration |
| **Thresholds & limits** | similarity cutoff, top_k, chunk size, retry count, backoff, page size, rate limits | configuration |
| **Endpoints & resources** | URLs, hosts, ports, bucket names, catalog/schema/table names, queue and topic names | configuration |
| **Secrets** | API keys, tokens, passwords, connection strings | secret store, injected as environment — never in committed configuration |
| **Business constants** | statuses, error codes, enum values, feature flags | a named constant or enum **in code** — defined once, referenced everywhere |

Rules:

- **Prompts and instructions are files, not string literals — including one-line ones.** A
  prompt that will be reviewed by a non-engineer, versioned, A/B tested or scored by an eval
  cannot live inside a function body. This is the single most-violated rule here, and the
  most expensive: it is what forces a redeploy to change a sentence.
- **Configuration is loaded and validated once at startup**, into a typed settings object,
  and **fails loudly on a missing or malformed key**. No `os.getenv` scattered through the
  code; no silent default that masks a misconfigured environment.
- Environment-specific values differ by configuration, never by branch, and never by an
  `if env == "prod"` in business logic.
- Test fixtures and test data are exempt. Everything in `src/` is not.

---

## Conformance

The audit checklist for this guideline lives beside it, in [`conformance/service-structure.md`](conformance/service-structure.md) — one file, one source of truth, loaded by whoever is auditing rather than by everyone who edits a file.
