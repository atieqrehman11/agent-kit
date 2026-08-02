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
