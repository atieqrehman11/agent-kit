# Release & Delivery Planning Guidelines

Applies to **every** plan, WBS, release plan, roadmap or estimate, in any project, any format
(xlsx, md, docx). These are nine ordered **gates**, not a menu. Do not start a later gate before
the earlier one passes. If the user asks for a Gantt chart on day one, the honest answer is that
the task list has to be complete, reviewed and estimated first — say so, then do the gates in
order.

```
1  Requirements          from code or specs, never assumption
2  Task list             complete, including the unglamorous work
3  Review                gaps, overlaps, phase triage           ← before you spend effort pricing
4  Priority              P0–P3 on every task
5  Estimates             man-days, nothing over 5
6  Dependencies          by ID, graph validated
7  Schedule → Gantt      resource-constrained; effort is not duration
8  Release plan          phases, milestones, binary exit gates
9  Final review          run the validator until clean
```

---

## Applies at every gate, not one of them — precision in questions and answers

This is a working rule, not a step. It governs how you behave inside all nine gates.

**Questions:** batch them, name the two or three options, and state which you recommend and why.
Never ask a question whose answer you could establish by reading the code.

**Answers:** give the number, then the reasoning. When something is a guess, label it as a guess
**in the artefact itself, in plain language, above the output** — never buried inside a formula.

**Why this matters concretely:** a sizing model reported an 8-day shortfall that came entirely
from one unconfirmed assumption. Because that assumption was written in plain text at the top of
the sheet, the user corrected it in a single sentence. Had it been inside a formula, a wrong
number would have travelled into a management deck. **A model's assumptions must be more visible
than its outputs.**

---

## Gate 1 — Requirements, from code or specs. Never from assumption.

Before writing a single task, establish what the system actually does today.

- Read the **code**, not the plan's description of the code. Open the entry points, the pipeline
  tasks, the config. Find what the real inputs and outputs are.
- Read the **specs, ADRs, design docs, prior decision records** if they exist.
- If neither exists for some part of the scope, say so explicitly and mark the plan
  *directional* for that part. Do not silently estimate an unknown.

**Failure mode this catches:** a plan said "Auto Loader on the source volume — 3 days". The code
showed the pipeline read a Unity Catalog Volume that *nothing populated*; sample files had been
placed by hand. The estimate covered stage two of a two-stage process where stage one did not
exist. No amount of reviewing the plan document would have found it. **8 days of missing work.**

---

## Gate 2 — The task list must be complete before anything else happens

Complete means: every task needed to reach the stated end state exists as a row, including the
unglamorous ones (secrets, environments, CI, runbooks, access requests). Assign each task its
workstream and its phase here — phase is an attribute of the task, not something invented later
when the release plan is written.

Ways to find what is missing:

- **Read every acceptance criterion as a list of required inputs.** If a criterion says
  "validated against an SME-labelled sample", there must be a task that *produces* that sample,
  with an owner and days. If not, the plan is assuming a person it never paid for.
- **Check every dependency on a decision.** If a task depends on an open decision, something must
  be scheduled to close that decision.
- **Walk the data/control flow end to end** and name the stage that moves each artefact. Missing
  work hides between stages, not inside them.

Assigning the phase is a triage decision, not a formatting one: essential work goes early,
enhancements go late or leave the plan. The procedure is [`triage.md`](triage.md) — the question is
never "is this important?" but **"if we ship without this, is the system missing something, or is it
wrong?"** Missing is deferrable; wrong is not.

**Failure mode this catches:** two real gaps in one review — an SME sample with no task, and a
canonical-selection rule depending on an open decision nobody was scheduled to answer.

---

## Gate 3 — Deep review of the task list, before you spend effort pricing it

A separate, deliberate pass, run by someone (or some agent) other than whoever wrote the list.
**This comes before priority and estimates on purpose:** pricing a list that contains duplicates,
or that is missing a prerequisite, wastes the estimating effort and then has to be redone. Check
for:

- **Overlaps** — two tasks doing the same work, or one task's scope quietly inside another's.
  When merging, keep the surviving row's wording precise about what it now covers.
- **Gaps** — re-run the Gate 2 techniques adversarially. Read acceptance criteria as required
  inputs; chase every dependency on an open decision.
- **Double counting.** If work moves from one task to another, the source task's scope must shrink
  by exactly what left it. Say the arithmetic out loud.
- **Fixed vs volume-driven cost.** Separate what scales with data, users or scope from what does
  not. Conflating them points anxiety at the wrong risk.
- **Challenge every phase assignment.** Argue each Phase-1 task down a phase and see what survives;
  argue each late task forward. Run `triage.py` for the mechanical shortlist, then apply the five
  KEEP tests in [`triage.md`](triage.md) — the acceptance-criterion test and the blast-radius test
  are the two that get missed. Of nine tasks deferred on the reference plan, three were restored
  once those tests were applied properly.

A second, much cheaper re-check belongs inside Gate 5, because a price is itself evidence: a task
that comes out surprisingly large is usually hiding scope or a missing prerequisite.

---

## Gate 4 — Prioritize every task

Every task carries a priority. Use a fixed scale and define it in the document:

```
P0 = blocker for the stated end state
P1 = required for go-live
P2 = required soon after
P3 = deferrable
```

No task may be left unprioritized. P0 count per phase is a headline number — report it.

---

## Gate 5 — Estimate in man-days, and cap every task at 5 days

- Estimate in **days of one person, hands-on-keyboard**. State explicitly that effort excludes
  review latency, client waiting time and management overhead.
- Publish the anchors so the numbers are auditable, e.g.
  `0.5 = a config change with a test · 1 = a contained code change · 2 = a small feature with
  tests · 3 = a feature across two layers · 5 = a subsystem`.
- **No task exceeds 5 days.** Anything larger is split along a *real seam* — a genuine technical
  boundary — and the parts carry suffixes (`D-01a`, `D-01b`, `D-01c`).
- Never use T-shirt sizes (S/M/L/XL) in a plan that has to be scheduled. They cannot be summed
  and they hide 3x ranges inside one letter.
- **Re-check for gaps the prices revealed.** A surprisingly large estimate usually means hidden
  scope or a missing prerequisite. This is the cheap follow-up to Gate 3, not a replacement for it.

**Why the cap earns its keep:** it is an estimation-quality device, not bookkeeping. Splitting
one 10-day task along its real seams revealed that one part depended on another part existing
first — and had been sitting in the wrong phase. **Anything you cannot split is something you do
not yet understand.**

---

## Gate 6 — Dependencies

- Every task records what it depends on, by ID.
- **Validate the graph.** No dangling IDs, no cycles, no inverted edges. Check direction task by
  task — a real plan once had a secrets task depending on drift detection, which is backwards.
- Distinguish dependencies on **tasks** from dependencies on **decisions**. Both block; only one
  is engineering work.
- Flag pairs: if task B exists only to contain task A's risk, record that as a written RULE next
  to both.

---

## Gate 7 — Schedule, then Gantt. Effort is not duration.

**This is the single most important lesson in this document.**

Total effort tells you almost nothing about duration. Build a **resource-constrained schedule**:
each person does one task at a time, at their allocation; a task starts when its dependencies
are done *and* its owner is free. Prioritise ready tasks by longest downstream chain.

- **A 50% role needs 2 calendar days per task-day. A 25% role needs 4.** Part-time roles are
  schedule multipliers and are the most common hidden constraint.
- **Level work across seats** — send each task to whoever can finish it soonest — rather than
  siloing by role. Reserve a role only where the skill genuinely cannot transfer.
- Use phase as a **scheduling priority**, not a hard gate. Hard-gating phases produced 26 weeks;
  letting them overlap with phase as a tie-break produced 12.9. If phases overlap, the document
  must say so.
- **Test levers, do not guess them.** Run the scenarios and report real numbers.

Observed on one plan:

| Action | Scope change | Schedule saved |
|---|---|---|
| Deferred 24.5 days of tasks | −10% | 0.7 weeks |
| Re-levelled work across seats | none | 2.7 weeks |

**Cutting scope was the weakest lever available.** Always build the schedule *before* discussing
what to cut, or you will negotiate away scope to buy days that were never on the critical path.

Then draw the Gantt from that one schedule — week-by-week bars, coloured by phase, one row per
task. Every date in every other sheet must come from this schedule and no other.

---

## Gate 8 — The release plan: phases, milestones and binary exit gates

**Milestones are not a separate gate — they are what the release plan is made of.** Treating them
as their own step invites the question "before or after the release plan?", and the answer is
neither: a release plan with no milestones is a list of dates, and milestones with no release plan
have nowhere to live. Build them together, once, here.

What must come *before* is the schedule (Gate 7), so the dates are **computed rather than chosen**.

A milestone has two halves, and they are settled at different times:

| Half | Where it comes from | When it is settled |
|---|---|---|
| **What is true at the boundary** — the demonstrable outcome and the binary exit gate | scope | drafted while phasing tasks in Gate 2; finalised here |
| **When it lands** — start week, end week, which month | the Gate 7 schedule | here, and only here |

Never reverse-engineer the first half to fit the second. A milestone written backwards from a date
it has to hit is how a plan starts lying.

Each phase gets:

- A **name** stating what exists at the end ("MVP on stage", not "Phase 1 complete")
- The **environment** it lands in
- An **entry condition** — what must be true to start
- A **binary exit gate** — every item true or the phase is not done
- **Effort, P0 days, task count, start week, end week** — all derived from the Gate 7 schedule

Milestones must be demonstrable. "Deduplication complete" is not a milestone; "signed and unsigned
copies of one agreement collapse to a single indexed document" is.

The release plan **does not repeat the task list** — tasks live in the backlog and are referenced
by ID. Copying tasks into the release plan creates a second truth that immediately drifts.

Also include: a month-by-month view for reporting, team allocation with utilisation per role per
phase, and any level-of-effort roles (PM, delivery) budgeted **explicitly and separately** from the
task backlog, since they are continuous rather than task-shaped. Rebuilding a plan purely from a
task backlog silently drops them.

---

## Gate 9 — Review carefully before delivering

Run this checklist every time, and fix what it finds before reporting done:

- [ ] **One source of truth.** The task list is authoritative; every other sheet or section is
      derived from it. No number appears in two places with two values.
- [ ] Totals reconcile: sum of tasks = phase totals = headline figure.
- [ ] Every dependency ID resolves. No cycles. Directions checked.
- [ ] No task over 5 days. Every task has priority, phase, owner, estimate, dependency,
      acceptance criteria.
- [ ] Every date traces to the one schedule.
- [ ] **No reference to removed or deferred work.** When something is deferred, sweep for
      orphaned references — risks whose *mitigation* was the deferred task now read as controlled
      and are silently false; checklist lines ask for evidence nothing will produce.
- [ ] Deferred items kept in a separate section with the reason and full original analysis, so
      they can return without redoing the thinking. Deferred pairs carry a RULE.
- [ ] Terminology consistent throughout (do not leave "Wave" language in a plan that now uses
      "Phase").
- [ ] Rounding: `0.5` days must not render as `0`. Check every formatted number.
- [ ] **Render and read the output** as the user will see it. For xlsx, verify formulas resolve
      and totals are visible; for diagrams, export to PNG and look at it.

---

## Deferral discipline

When removing scope, three things need checking:

1. **Pairs.** If B exists only to contain A's risk, deferring A makes B pointless — but
   reinstating A without B is dangerous. Write the RULE beside both rows.
2. **Blast radius.** Sweep risks, checklists and acceptance criteria for anything whose control
   was the deferred task.
3. **Do not over-correct.** Before cutting, separate *why each part exists*. One error made:
   removing an SME *volume review queue* (correct — it only existed for a deferred technique) and
   an SME *sign-off* (wrong — mandatory regardless) in a single move, because both were filed
   under "SME". They were different things sharing a label: one scaled with the data, one was
   fixed and required.

---

## Mechanics that prevent silent corruption

- **Never address data by column position.** Build a header→index map and look up by name. Users
  reorder columns for readability, and position-based access then reads the wrong column and
  returns plausible garbage. Hard-coded `SUMIFS` column letters break the same way — they
  silently summed a text column and returned zero.
- **Reports static, models live.** A summary sheet should hold written-in values (a formula
  referencing a moved column goes blank). A sizing model must stay editable with live formulas
  scoped *inside its own sheet*. Set `fullCalcOnLoad` so Excel recalculates on open.
- **Generate the artefact with a script**, not by hand-editing, so it can be regenerated when the
  task list changes. Back up before each write.
- **Warn if the user has the file open.** An application holding the file can overwrite generated
  output with its own stale copy.

---

## Recommended artefact structure

```
00 Overview            purpose, scope in/out, plan-in-one-block, legend
01 Readiness baseline  dimensions scored, the gap, the tasks that close it
02 Task Backlog        THE SOURCE OF TRUTH — id, workstream, task, days,
                       priority, phase, owner, dependency, current state,
                       work required, acceptance criteria
02a Effort Summary     by workstream / phase / owner (derived, static)
02b Deferred           what was cut, why, and the full original analysis
04 Release Plan        phases with entry condition and binary exit gate
04a Month by Month     reporting view
04b Gantt              the one schedule — every date comes from here
05 Team Allocation     task days vs booked days, utilisation, LOE roles
0x Sizing models       live formulas, assumptions stated in plain text on top
1x Go-live checklist   binary sign-off, evidence named per line
1x Risks               severity, likelihood, mitigation by task ID, phase
1x Decisions           decided and open, each with a recommendation and owner
Scope classification   new function vs hardening — governance, placed last
```

Order gates before aesthetics. A beautiful Gantt over an incomplete task list is worse than no
Gantt, because it looks finished.
