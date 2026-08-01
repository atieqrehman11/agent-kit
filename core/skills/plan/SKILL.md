---
name: plan
kind: skill
description: >
  Produce a release plan, WBS, roadmap or delivery estimate from a codebase or a set of
  specs — requirements, task list, review, priorities, estimates, dependencies, a
  resource-constrained schedule, and a release plan with binary exit gates. Use for any
  planning or estimating request, in any format.
requires:
  python: [openpyxl]
---

# Plan

Nine ordered gates. A later gate does not start before the earlier one passes. If asked
for a Gantt on day one, say that the task list has to be complete, reviewed and estimated
first — then run the gates in order.

The single most important rule: **effort is not duration.** Build a resource-constrained
schedule before discussing what to cut, or scope gets negotiated away to buy days that
were never on the critical path.

## Entry points

- `/plan:release` — run the gates and produce the artefact

## Payload

- `reference/planning.md` — the nine gates, in full, with the failure mode each catches
- `reference/triage.md` — the essential-vs-enhancement deferral test
- `validate.py` · `schedule.py` · `triage.py` — the mechanical checks and the scheduler

A model's assumptions must be more visible than its outputs: state guesses in plain
language above the artefact, never buried inside a formula.
