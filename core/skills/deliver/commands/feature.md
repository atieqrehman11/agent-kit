---
name: feature
kind: command
description: >
  Build one stated requirement end to end without supervision — acceptance criteria, design,
  implementation against the repo's standards, independent review, a bounded fix loop, tests,
  and a written report. Use when you know what you want and want the finished, reviewed
  result handed back rather than driving each step yourself.
arguments: "[the requirement, in your own words]"
---

# Deliver a feature

The requirement:

```
{{args}}
```

If that is empty, ask what to build and stop. Everything below needs a requirement.

## Run it

Read [`../reference/gates.md`](__SKILL_DIR__/reference/gates.md) and run gates 0 → 7 in
order. Do not skip forward; do not start gate 3 before gate 2 has produced a design.

Announce each gate as you enter it, in one line, so a user watching can follow along and a
user reading later can see where it stopped:

```
── Gate 3 · Build ─────────────────────────────
```

## The four rules you are most likely to break

1. **Bounded fix loop.** Three rounds. On a fourth `FAIL`, stop, report `BLOCKED`, and name
   the outstanding findings. Do not keep going because you feel close.
2. **The review is not yours.** Dispatch the `reviewer` subagent and copy its verdict in
   verbatim, including anything unflattering. Do not soften it and do not paraphrase it.
3. **Run the tests, paste the output.** Not "tests pass". Never weaken a test or narrow a
   criterion to reach green — a failing test in the report is information; a quietly relaxed
   assertion is a lie.
4. **Branch, do not publish.** Work on `deliver/<slug>`. Do not push, open a pull request,
   deploy, or touch CI unless the requirement said to.

## Finish

Write the report to `docs/delivery/<slug>.md`, then return exactly five lines plus the path:

```
Verdict     PASS | PASS_WITH_CONDITIONS | BLOCKED
Criteria    n of m met
Tests       n passed, n failed
Left        the most important thing outstanding, or "nothing"
Assumed     the assumption that would most change the result if wrong
Report      docs/delivery/<slug>.md
```
