# Gen AI Platform — Codex Agent Configuration

## Available Roles

When asked to act in a specific role, read the corresponding agent file before responding.
Each file contains the full role definition, behaviour rules, and output format.

| Role | Agent File |
|---|---|
| Architect | core/guidelines/design.md |
| Python Developer | core/guidelines/python-llm.md |
| React Developer | core/guidelines/react.md |
| Java Developer | core/guidelines/java.md |
| Chainlit Developer | core/guidelines/chainlit.md |
| Streamlit Developer | core/guidelines/streamlit.md |
| QA Engineer | core/subagents/qa.md |
| Reviewer | core/subagents/reviewer.md |
| Decomposer | (CUT - was plan Gate 2 with a forbidden sizing scale) |

## Platform Guidelines

Read these before starting any work in this platform:

- API Standards: core/guidelines/api.md
- Chat API Standards: (client-owned; not in core/)
- Architecture Diagrams: core/skills/diagram/reference/architecture.md

## Project Context

The project Context Block is in this project's AGENTS.md.
Extract stack, constraints, and design principles from it silently.
Do not ask for context that is already there.
