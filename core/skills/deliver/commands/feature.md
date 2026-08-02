---
name: feature
kind: command
description: >
  Build one requirement end to end without supervision — acceptance criteria, design, task
  list, implementation against the repo's standards, independent review, a bounded fix loop,
  tests, and a written report. Reads an approved spec if one exists and derives one if it
  does not. Use when you want the finished, reviewed result handed back rather than driving
  each step yourself.
arguments: "[the requirement, in your own words — or the slug of a spec already written]"
---

# Deliver a feature

The input:

```
{{args}}
```

If that is empty, ask what to build and stop. Everything below needs a requirement or a slug.

## Run it

Read [`../reference/gates.md`](__SKILL_DIR__/reference/gates.md) and run gates 0 → 8 in
order. Do not skip forward; do not start gate 4 before gate 3 has produced a task list.

Announce each gate as you enter it, in one line, so a user watching can follow along and a
user reading later can see where it stopped:

```
── Gate 4 · Build ─────────────────────────────
```

### Start by looking for a spec

Gates 0, 2 and 3 produce **documents**. Before running one, look for its file:

```
gate 0 / 2 / 3 input  =  docs/specs/<slug>/<doc>.md if present  >  derive it now
```

- **Present** — load it, check its `derived-from` hash against its upstream, and move on.
  Announce the gate as `loaded` rather than running it. Do not re-derive a document that
  exists; you would produce a second answer to a settled question.
- **Absent** — derive it *and write it* to `docs/specs/<slug>/`, from the template. An
  unsupervised run leaves the same three documents behind that {{cmd:deliver:spec}} would
  have, which is what makes the result resumable and reviewable.
- **Stale** (`derived-from` hash does not match the upstream file) — re-derive that document
  and everything below it, and say so in the report. Never build against a design whose
  requirements moved.

Gate 1 is different: it produces **context**, not a document, so it runs every time. A spec
can name which standards apply; it cannot put them in your context for you.

## The five rules you are most likely to break

1. **Write the documents you derive.** If you frame criteria in your head and go straight to
   code, the run is unauditable and the next iteration starts from nothing. The three
   documents are part of the deliverable, not a byproduct of the supervised path.
2. **Bounded fix loop.** Three rounds. On a fourth `FAIL`, stop, report `BLOCKED`, and name
   the outstanding findings. Do not keep going because you feel close.
3. **Neither check is yours.** Dispatch the `critic` subagent at gate 0 and the `reviewer`
   subagent at gate 5, each without your reasoning. Copy the reviewer's verdict in verbatim,
   including anything unflattering — do not soften it and do not paraphrase it. Resolve every
   critic finding into a criterion or a stated exclusion; running unsupervised is not licence
   to dismiss one.
4. **Run the tests, paste the output.** Not "tests pass". Never weaken a test or narrow a
   criterion to reach green — a failing test in the report is information; a quietly relaxed
   assertion is a lie.
5. **Branch, do not publish.** Work on `deliver/<slug>`. Do not push, open a pull request,
   deploy, or touch CI unless the requirement said to.

## Finish

Write the report to `docs/specs/<slug>/report.md`, beside the three documents it closes out,
then return exactly five lines plus the path:

```
Verdict     PASS | PASS_WITH_CONDITIONS | BLOCKED
Criteria    n of m met
Tests       n passed, n failed
Left        the most important thing outstanding, or "nothing"
Assumed     the assumption that would most change the result if wrong
Report      docs/specs/<slug>/report.md
```
