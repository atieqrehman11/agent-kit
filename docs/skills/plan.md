# plan

A Claude Code skill for producing release plans that are **scheduled and validated before they are
shown** — task backlog, priorities, man-day estimates, dependencies, Gantt, milestones.

| Command | What it does | Direction |
|---|---|---|
| [`/plan:release`](release.md) | Read the code, ask one batched round of questions, then author, schedule, validate and report a full release plan. | codebase → `.xlsx` plan |

## Why it exists

Generated plans fail in the same few ways every time:

- **Built from the previous plan, not from the code.** One plan read *"Auto Loader on the source
  volume — 3 days"*, which was perfectly reasonable. The code showed the pipeline read a Unity
  Catalog Volume that nothing populated — sample files had been placed there by hand. Eight days of
  missing work that no document review would have found.
- **Work assumed but never scheduled.** An acceptance criterion read *"no false positives on an
  SME-labelled sample"*. No task produced that sample: the plan assumed a person it never paid for.
- **Total effort passed off as a duration.** 250 days across 6 FTE is not 8 weeks. It was 12.9.
- **Numbers that contradict each other.** One inherited workbook carried 301 days on its overview,
  262 in its backlog, and separate arithmetic on two WBS sheets. Three truths, no way to tell which
  was current.

## The design rule

**Async where the work is mechanical, blocking exactly once for facts only the user has.**

Fully autonomous planning produces confidently wrong plans, which is worse than slow. Three single
sentences from the user each changed a real plan materially — one location instead of four, an SME
sign-off that must not be skipped, and a confirmed source architecture. So the skill front-loads
everything answerable from the code, asks one batched round, then runs to completion.

## Is the plan front-loaded?

The question the skill answers at Gate 3: which tasks are **enhancements** that belong later (or
nowhere), and which cheap tasks should be **pulled forward** because expensive work queues behind
them.

```bash
python3 triage.py --backlog PLAN.xlsx
```

Candidates are **tiered**, because "nothing depends on it" is a weak signal on its own — tests,
runbooks and penetration testing are leaves by nature and every one of them is required:

| Tier | Meaning |
|---|---|
| `CANNOT DEFER` | something depends on it, or another task's acceptance criterion names it |
| `DEFERRING ORPHANS A CONTROL` | named as a risk mitigation or checklist evidence — defer and that risk reads as mitigated when it is not |
| `ENHANCEMENT CANDIDATES` | P2/P3, no dependents, uncited. The real shortlist |
| `ASSURANCE LEAVES` | P0/P1 with no dependents. Removable, but required — a warning, not scope |
| `PULL EARLIER` | cheap task gating expensive work. Belongs in week 1 whatever its priority says |
| `MISPLACED` · `PAIRS` | phase and priority disagree · defer both or neither |

On the reference plan it found `D-14` (1.5d gating 23.5d) and `Q-00` (2d gating 15d) as pull-earlier
gates, and **zero enhancement candidates** — correctly, because that plan had already been triaged.

The judgement the script refuses to make is in
[`reference/triage.md`](reference/triage.md): five patterns that mean defer, and five tests where
any one firing means keep. The question is never "is this important?" but **"if we ship without
this, is the system missing something, or is it wrong?"** Missing is deferrable; wrong is not.

Expect the shortlist to shrink. Of nine tasks deferred on the reference plan, **three were restored**
once the KEEP tests were applied properly — the acceptance-criterion test and the blast-radius test
are the two that get missed.

## The three scripts do the arithmetic

An LLM asked to compute a resource-constrained schedule produces plausible wrong numbers. These
give the same answer every time, in a second, and can be re-run free.

```bash
# what does the plan actually take, and what is the binding constraint?
python3 schedule.py --backlog PLAN.xlsx --alloc team.json --level

# measure the lever instead of guessing it
python3 schedule.py --backlog PLAN.xlsx --alloc team.json --scenarios

# Gate 9 — exit 1 means not deliverable
python3 validate.py --backlog PLAN.xlsx --stale Wave --cap 5
```

`schedule.py` reports a **binding chain** rather than a critical path: it follows waits for a busy
seat as well as dependency edges, because in a resource-constrained plan the finish date is usually
set by a mix of both. Following dependencies alone reported a 2-task chain driving a 12.9-week plan.

`--scenarios` is the output worth having on day one. On the reference plan:

```
as configured                        12.90 wks
Data Platform Architect at 100%      11.90 wks  +1.00
Platform & DevOps at 100%            11.90 wks  +1.00
Legal SME (client) at 100%           12.20 wks  +0.70
every part-time seat at 100%         10.20 wks  +2.70
```

Part-time seats were worth 2.7 weeks — a measured negotiating position rather than an opinion.

`validate.py` catches what is invisible on screen but wrong in substance: dangling and cyclic
dependencies, tasks over the size cap, duplicate IDs, rows missing a priority or an owner,
fractional days hidden by a 0-decimal number format, stale terminology left after a rename, and
**orphaned references** — another sheet citing a task that was deferred or deleted, which silently
falsifies any risk whose mitigation was that task.

Both were verified by reproducing an existing 105-task / 250.5-day / 12.9-week plan exactly.

## The standard

[`reference/planning.md`](reference/planning.md) — nine ordered gates, each carrying the failure
mode it catches, plus deferral discipline and the mechanics that prevent silent corruption.
[`reference/triage.md`](reference/triage.md) — the essential-or-enhancement decision procedure used
at Gates 2 and 3.

The order that matters most: **review comes at Gate 3, before priority and estimates**, because
pricing a list that still contains duplicates or gaps wastes the estimating effort. And
**milestones are not their own gate** — they are what the release plan is made of, built at Gate 8
once the schedule exists so the dates are computed rather than chosen.

## Layout

```
plan/
  release.md              /plan:release — the operating procedure
  schedule.py             resource-constrained scheduler, Gantt writer, lever tester
  triage.py               essential-vs-enhancement shortlist, pull-earlier gates
  validate.py             Gate 9 validator
  reference/
    planning.md           the standard: nine ordered gates
    triage.md             the deferral test: 5 defer patterns, 5 keep tests
```
