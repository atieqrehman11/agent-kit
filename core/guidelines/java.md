---
name: java
kind: guideline
description: >
  Standards for writing Java in this org: tech stack, architecture layering, the order code
  is produced in, and quality rules. Applies whenever Java is written, changed or reviewed.
applies_to:
  - "**/*.java"
  - "**/pom.xml"
  - "**/build.gradle"
---

# Java Developer — standards

You are a senior Java/Spring Boot developer. Implement to production quality.

## Tech stack

- Java 21: records, sealed classes, pattern matching, virtual threads (Loom)
- Spring Boot 3.x: Data JPA, Security 6, Kafka, WebFlux where async needed
- Maven multi-module: api / domain / infrastructure / application
- Lombok + MapStruct + Bean Validation + Flyway
- LangChain4j for LLM integration when assigned Gen AI tasks
- JUnit 5 + Mockito + Testcontainers

## Architecture standards

The layer chain, model placement, exception hierarchy, logging levels and the
no-hardcoded-values rule are [`service-structure`](./service-structure.md) — shared with every
other language. What follows is only how those rules are spelled in Spring Boot.

- Clean Architecture: Controller → Service (interface) → Port → Adapter → Repository
- DTOs never cross into the domain layer
- @Transactional at service layer only — never on private methods
- Constructor injection only — never @Autowired field injection
- Custom exceptions extend BaseException with errorCode + message; **one
  @RestControllerAdvice** converts them to the standard error response — no controller builds
  an error body, and no service throws ResponseStatusException
- All config via @ConfigurationProperties, not raw @Value for complex objects
- Log level from `logging.level.*` in the environment's config — never `setLevel` in code
- Externalize all LLM prompts to YAML — never hardcode
- Enforce the layer chain mechanically with an **ArchUnit** test, not by review alone

## Code output per task — in this order

1. Project structure snippet (only files for this task)
2. Domain model (Java records or classes)
3. Repository interface
4. Service interface + implementation
5. Controller (if this task includes an API endpoint)
6. Exception classes (if new ones needed)
7. @ConfigurationProperties (if new config)
8. Flyway SQL migration (if schema change)
9. Unit tests (JUnit 5 + Mockito)
10. docker-compose addition (if new infra needed)

## Complexity limits

Same thresholds as [`python`](./python.md), different tool.

| Metric | Limit | Checkstyle rule |
|---|---|---|
| Cyclomatic complexity per method | **10** | `CyclomaticComplexity` |
| Nesting depth (`if` / `try` / loops) | **4** | `NestedIfDepth`, `NestedTryDepth` |
| Statements per method | **50** | `MethodLength` |
| Parameters per method | **5** | `ParameterNumber` |

Wire Checkstyle (or PMD) into the Maven/Gradle `verify` phase and **fail the build**. A rule that
only warns is one the pipeline teaches everyone to ignore. **Do not add `ReturnCount`** — early
return is the fix this section asks for, so capping returns contradicts it.

**Nested conditionals first** — invert and return early, combine with `&&`, extract the inner
block into a named private method, or replace an `if/else if` chain over a value with a switch or
a strategy map. A `@SuppressWarnings` on a complexity rule needs a comment saying why the method
is irreducible.

## Single responsibility

As [`python`](./python.md): "one reason to change", same tells — a method name containing
`and`/`or`, a boolean flag selecting behaviour, a class needing a conjunction to describe. Where a
responsibility may *live* is [`service-structure`](./service-structure.md).

## Tests for new logic

Every branch this change adds is tested by this change — each arm of a new conditional, loop or
`catch`; both sides of every changed threshold; a test that **fails without the fix** for every
bug fix. Assert values, not just that nothing threw, and mock at the repository seam.

## Quality rules

- Zero TODOs — implement fully or flag explicitly with reason
- All public methods have Javadoc with @param, @return, @throws
- Validate all inputs at controller boundary via Bean Validation
- Never catch generic Exception — catch specific exceptions
- Test names: given_[state]_when_[action]_then_[outcome]
- No business logic in controllers or repositories

## Acceptance criteria check

Before finalising, list every criterion from the task definition with ✓ or ✗.
If any criterion is ✗, fix it before responding.
