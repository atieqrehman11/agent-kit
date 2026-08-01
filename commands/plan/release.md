# Build a release plan from a codebase, scheduled and validated before it is shown

Produce a complete release plan — task backlog, priorities, man-day estimates, dependencies,
resource-constrained schedule, Gantt, milestones — that is **already correct the first time you
show it**. The recurring failures this exists to prevent: a plan built from the previous plan
rather than from the code, work that is assumed but never scheduled, a total-effort figure passed
off as a duration, and numbers that contradict each other across sheets.

The standard is [`reference/planning.md`](reference/planning.md). It defines nine **ordered gates**,
and each step below names the gate it satisfies. Do not start a later gate before the earlier one
passes, and say so plainly if the user asks for a Gantt before the task list is complete, reviewed
and estimated.

---

## The one design rule

**Run async where the work is mechanical. Block exactly once, for facts only the user has.**

Do not iterate with the user gate by gate — that is the thing this skill exists to remove. Do not
go fully autonomous either: a plan built without the user's private facts is confidently wrong,
which is worse than slow. Three single sentences that each changed a real plan materially:

- *"we will read all docs from one location, that is Google drive"* → demolished a reported 8-day
  gap that came entirely from a guessed input.
- *"ideally we would need SME — it shouldnt be skipped"* → restored 3 days of mandatory work cut
  by over-correction.
- *"ETL will run and pull from Gdrive and bring to bronze schema"* → confirmed a whole missing
  pipeline stage worth 8.5 days.

Gather everything answerable from the code first, ask **one** batched round, then run to the end.

---

## Step 1 — Discovery (async, parallel) — Gate 1

Fan out `Explore` subagents in a single message, one per area, each returning findings only:

- entry points, pipelines and jobs: what actually runs, and what it reads and writes
- config, environments, secrets, CI files: what exists versus what is assumed to exist
- tests and evaluation: what is covered, what is run by hand, what gates nothing
- docs, ADRs and prior decision records
- any existing plan or WBS — treat it as a **claim to verify**, never as a source

**Verify the plan against the code, never against itself.** A prior plan read *"Auto Loader on the
source volume — 3 days"*, which was entirely reasonable. The code showed the pipeline read a Unity
Catalog Volume that nothing populated; sample files had been placed there by hand. That was 8 days
of missing work no document review would have found.

Write the current-state map down before continuing.

## Step 2 — The single blocking question round (the only place this stops)

Batch **every** question into one `AskUserQuestion` call. It allows four questions, so pick the
four that change the most; anything beyond four goes in one short numbered list in the message.

Ask only what the code cannot answer:

- team shape and allocation per role — this drives duration more than scope does
- the target date, and whether it is a constraint or an aspiration
- systems of record, access that must be requested, and who grants it
- which decisions are already made versus open, and who owns the open ones
- the scope boundary: what is explicitly out

**Never ask** anything discoverable by reading the repo, and never ask the same thing twice in
different words. Put your recommendation inside each question so silence is a safe default.

## Step 3 — Author the complete task list (async) — Gate 2

Author the backlog. Every row carries: `id · workstream · task · phase · owner · depends on ·
current state · work required · acceptance criteria`. Priority and days come at Step 5 — leave
those two columns empty for now, on purpose.

Assign each task its **phase** here. Phase is an attribute of the task, not something invented
later when the release plan is written — and it is a triage decision. Essential work goes early,
enhancements go late or leave the plan. Apply [`reference/triage.md`](reference/triage.md): the
question is not "is this important?" but **"if we ship without this, is the system missing
something, or is it wrong?"** Missing is deferrable; wrong is not.

Completeness means the unglamorous work is in the list too: secrets, environments, CI, runbooks,
access requests. Find what is missing by reading every acceptance criterion as a list of required
inputs, chasing every dependency on an open decision, and walking the data flow end to end naming
the stage that moves each artefact.

## Step 4 — Adversarial review, BEFORE pricing anything (async, a fresh agent) — Gate 3

Spawn a **separate** subagent whose only job is to attack the list. Never let the authoring agent
review its own work.

**This runs before priority and estimates on purpose.** Pricing a list that contains duplicates,
or that is missing a prerequisite, wastes the estimating effort and then has to be redone.

Its brief:

1. Read every acceptance criterion as a list of required inputs. Where a criterion names an
   artefact, sample, dataset or person, find the task that *produces* it. Report each one that has
   no task, no owner and no days.
2. Find every dependency on an open decision with nothing scheduled to close it.
3. Find overlaps — two tasks doing the same work, or one task's scope quietly inside another's.
4. Separate fixed cost from volume-driven cost wherever a sizing assumption appears.
5. Challenge every phase assignment — argue each Phase-1 task down a phase and each late task
   forward. Start from the mechanical shortlist:

```bash
python3 __SKILL_DIR__/triage.py --backlog PLAN.xlsx
```

   Then apply the five KEEP tests in [`reference/triage.md`](reference/triage.md). Read
   `ENHANCEMENT CANDIDATES` as the real shortlist and `ASSURANCE LEAVES` as a warning, not scope —
   tests, runbooks and sign-off have no dependents by nature and are all required. Act on
   `PULL EARLIER`: a cheap task gating expensive work belongs in week 1 whatever its priority says.

On a 105-task plan this pass found two real holes: an acceptance criterion requiring an
SME-labelled sample that no task produced, and a canonical-selection rule depending on a decision
nobody was scheduled to answer.

## Step 5 — Priority and estimates (async) — Gates 4 and 5

Only now that the list is complete and deduplicated:

- Priority `P0/P1/P2/P3`, with the scale defined in the document. Nothing left unprioritized.
- Days of one engineer, hands-on; state that effort excludes review latency, client waiting time
  and management overhead. Publish the anchors.
- **No task over 5 days.** Split along a real technical seam and suffix the parts (`D-01a`,
  `D-01b`). Anything you cannot split is something you do not yet understand.
- If work moves between tasks the source estimate **comes down**. Say the arithmetic out loud:
  moving 1.5 days out of a 5-day task makes it 4 — net +0.5, not +1.5.
- **Re-check for gaps the prices revealed.** A task that comes out surprisingly large is usually
  hiding scope or a missing prerequisite. Cheap follow-up to Step 4, not a replacement for it.

## Step 6 — Schedule and Gantt (deterministic, never an LLM) — Gates 6 and 7

Effort is not duration. Write `team.json` (format documented in `schedule.py --help`), then:

```bash
python3 __SKILL_DIR__/schedule.py --backlog PLAN.xlsx --alloc team.json --level
python3 __SKILL_DIR__/schedule.py --backlog PLAN.xlsx --alloc team.json --scenarios
python3 __SKILL_DIR__/schedule.py --backlog PLAN.xlsx --alloc team.json --level \
        --gantt "04b Gantt" --gantt-after "04a Month by Month" --apply
```

`schedule.py` refuses to run on a broken dependency graph, so it doubles as the Gate 6 check.

Read the **binding chain** in the output. It reports how much of the finish date is spent waiting
for *work* versus waiting for *people*. If seat waits exceed dependency waits, re-levelling or
raising an allocation shortens the plan more than cutting scope will.

**Never estimate a schedule in prose, and never recommend a lever without running `--scenarios`
first.** Measured on a real plan: deferring 24.5 days of scope bought 0.7 weeks, while re-levelling
bought 2.7 weeks with no scope cut at all. Cutting scope is usually the weakest lever available.

## Step 7 — The release plan, milestones included — Gate 8

**Milestones are not a separate step — they are what the release plan is made of.** Build them
together, here, once the schedule exists so the dates are computed rather than chosen.

Phases with an entry condition and a **binary** exit gate, each stated as something demonstrable
("signed and unsigned copies of one agreement collapse to a single indexed document", not
"deduplication complete"). Every figure — effort, P0 days, task count, start week, end week — comes
from the Step 6 schedule and from nowhere else.

Never reverse-engineer an exit gate to fit a date it has to hit. What is true at a boundary comes
from scope and was drafted when tasks were phased in Step 3; when it lands comes from the schedule.

The release plan **does not repeat the task list**; it references IDs. Level-of-effort roles (PM,
delivery) are budgeted explicitly and separately, since they are continuous rather than
task-shaped — rebuilding a plan purely from a task backlog silently drops them.

## Step 8 — Validate, and loop until clean — Gate 9

```bash
python3 __SKILL_DIR__/validate.py --backlog PLAN.xlsx --stale Wave --stale XL --cap 5
```

Exit code 1 means not deliverable. Fix and re-run.

Pay particular attention to the deferred-reference warnings. Deferring work silently falsifies
risks whose *mitigation* was that task, and checklist lines that ask for evidence nothing will now
produce — on one plan that was two risks reading as controlled and four unverifiable sign-off
lines.

Then read the rendered output as the user will see it: open the sheets, confirm formulas resolved
and totals are visible.

## Step 9 — Report

Lead with four numbers: tasks, days, duration, team. Then what is genuinely new versus what is
hardening what already exists. Then the asks of the client, and the principal risk. Keep it short
enough to paste into an email.

---

## Non-negotiables

- **One source of truth.** The task backlog. Every other sheet is derived and regenerable. Never
  let a number live in two places with two values.
- **Header-driven access only.** Look columns up by heading text, never by position — users reorder
  columns for readability and position-based reads then return plausible garbage. Hard-coded
  `SUMIFS` column letters fail the same way: they silently summed a text column and returned zero.
- **Reports static, models live.** Summary sheets hold written-in values; sizing models keep live
  formulas scoped inside their own sheet. Set `fullCalcOnLoad` so Excel recalculates on open.
- **Back up before every write**, and generate with a script so the artefact can be regenerated
  whenever the backlog changes.
- **Check for a lock file** (`~$NAME.xlsx`) before writing. If the workbook is open in Excel, its
  next save overwrites generated output with its stale copy — this has already destroyed three
  scripts' output once. Warn instead of writing.
- **Label guesses in the artefact, in plain language, above the output.** An assumption buried in a
  formula travels into a management deck; one written at the top gets corrected in a sentence.
- **Before cutting anything, separate why each part exists.** Removing a volume-driven review queue
  and a mandatory fixed sign-off in a single move, because both were filed under "SME", was the
  worst error of the reference engagement.
