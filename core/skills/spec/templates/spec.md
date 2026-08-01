# TPLVAR_ID — TPLVAR_TITLE

**Status:** DRAFT · **Created:** TPLVAR_DATE · **System:** TPLVAR_SYSTEM

TPLVAR_DESCRIPTION

## Repos Touched

Every repo this feature changes. A repo listed here MUST have at least one task in
`tasks.md`; a task MUST name a repo listed here.

| Repo | Type | What changes here |
|---|---|---|
TPLVAR_REPO_ROWS

## Requirements

One row per requirement. `FR` = functional, `NFR` = non-functional. Every ID here MUST
appear in some task's `Covers` column — `spec.py check` fails otherwise.

Acceptance criteria live here and nowhere else. Read each one as a list of required
inputs: if it says "validated against an SME-labelled sample", a task MUST exist that
*produces* that sample.

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-01 | TODO_SET_REQUIREMENT | TODO_SET_ACCEPTANCE |

## Design

How it works. Keep it to what a reviewer needs to disagree with — interfaces, data flow,
and the decisions that were not obvious. Do not restate the requirements.

TODO_SET_DESIGN

### Contracts

Interfaces crossing a repo boundary — endpoints, table schemas, event payloads, tool
signatures. A contract change is the most common source of cross-repo breakage, so name
both sides.

| Contract | Producer repo | Consumer repo | Shape |
|---|---|---|---|
| TODO_SET_CONTRACT | | | |

## Open Decisions

A task that depends on an open decision cannot start. Every open decision MUST have an
owner and a `Needed by` date, and `spec.py check` reports any that are still open.

| ID | Decision | Options | Recommendation | Owner | Needed by | Status |
|---|---|---|---|---|---|---|
| D-01 | TODO_SET_DECISION | | | | | OPEN |

## Out of Scope

What this feature deliberately does not do. Stops scope creep during implementation.

- TODO_SET_OUT_OF_SCOPE

## Assumptions

Anything believed but not verified from code or a spec. State it in plain language here —
an assumption buried in a task estimate travels into a management deck uncorrected.

- TODO_SET_ASSUMPTION
