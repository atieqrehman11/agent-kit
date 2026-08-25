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

Ten ordered gates. A later gate does not start before the earlier one passes. If asked
for a Gantt on day one, say that the task list has to be complete, reviewed and estimated
first — then run the gates in order.

**Gate 0 first, every time: plan what was asked for, at the size it was asked for.** Match the
deliverable shape exactly — three sheets means three sheets — and state a size sanity-check before
writing tasks. A small feature is a small plan. Reserve the heavy machinery (large backlogs,
adversarial review, levelled Gantts) for genuinely programme-sized work; running it over a light
request produces a heavy answer that reads as a misunderstanding. Body text 11pt or above — an
artefact nobody can read has not been delivered.

**Build one sheet at a time.** Produce the first sheet, show it, stop. Continue only when asked.
A full multi-sheet workbook only on an explicit request for the full plan — a wrong assumption in
sheet one otherwise propagates into every derived sheet. Build order follows the gates (task list
first, since everything derives from it), not the order the user listed the sheets in.

The Gate 3 review finds gaps and overlaps **inside** the requested scope. It does not set the
scope. Triage its findings: accept what is missing or double-counted, record the rest as a
recommendation, and say what you declined. Accepting a review wholesale is the same failure as
skipping it.

The single most important rule: **effort is not duration.** Build a resource-constrained
schedule before discussing what to cut, or scope gets negotiated away to buy days that
were never on the critical path.

## Entry points

- `{{cmd:plan:release}}` — run the gates and produce the artefact

## Payload

- `reference/planning.md` — the nine gates, in full, with the failure mode each catches
- `reference/triage.md` — the essential-vs-enhancement deferral test
- `validate.py` · `schedule.py` · `triage.py` — the mechanical checks and the scheduler

A model's assumptions must be more visible than its outputs: state guesses in plain
language above the artefact, never buried inside a formula.
