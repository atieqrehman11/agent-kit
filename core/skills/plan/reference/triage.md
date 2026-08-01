# Essential or Enhancement — the deferral test

Used at **Gate 2** (assigning each task its phase) and challenged at **Gate 3** (the review).
Purpose: the most critical work sits at the START of the plan, and anything that merely improves
the outcome sits at the end or leaves the plan entirely.

`triage.py` shortlists the candidates mechanically. This document is the judgement it refuses to
make. Run the script first, then put every candidate through the tests below.

---

## The question is not "is this important?"

Everything in a plan is important or it would not be there. The question is narrower:

> **If we ship without this, is the system missing something, or is it wrong?**

Missing is deferrable. Wrong is not. A system that lacks a feedback button is missing something. A
system that merges two different contracts into one indexed document is wrong, and confidently so.
That distinction decides almost every case.

---

## Five patterns that mean DEFER

Each is a real call from a 105-task plan, with the reasoning that survived review.

**1. It improves the outcome over time; it is not needed to produce the outcome.**
The feedback endpoint (`S-09`). Ratings make future answers better. They are not needed to serve an
answer today, and the audit trail already reconstructs any answer, so a wrong one can still be
investigated. → Deferred.

**2. Something already in the plan achieves the same protection by another route.**
The chunk foreign-key re-point (`X-01c`). Its production benefit — no duplicate chunks in
retrieval — comes entirely from the index filter that is already in the plan. What is left is a
formal tidy-up. → Deferred. **Name the mechanism that covers it**, or this becomes wishful thinking.

**3. It measures something another measure already gates.**
Duplicate-precision measurement (`X-11`) and named evaluation slices (`E-06`). Precision is 100% by
construction with deterministic hashing, and the overall correctness score still gates releases
without slices. → Deferred. Failure analysis stays manual, as it already is.

**4. It has no observed driving condition.**
Near-duplicate fuzzy matching (`X-05`). The design justified it by "OCR variance and trivial
redlines" — a fifth condition nobody had ever observed. The four documented conditions are all
resolved by exact and normalised hashing. → Deferred, **and record what would trigger reinstating
it** so the decision can be revisited on evidence rather than memory.

**5. It is only needed if a capability ships that is not shipping.**
The quarantine table (`X-10`) is only needed if the pipeline deletes, and nothing in the plan
deletes. The amendment guard (`X-06`) exists only to contain fuzzy matching's risk, and fuzzy
matching is deferred. → Deferred **as a pair with the thing that needs them**, with a written RULE.

---

## Five tests that mean KEEP — any one fires and it cannot be deferred

Run all five. They are cheap and they are the ones that were nearly missed.

**1. The acceptance-criterion test.** Does any remaining task's acceptance criterion require it?

`X-04`'s criterion read *"no false positives on an SME-labelled sample."* The task producing that
sample did not exist — and when it was written, the instinct was to defer it as "review overhead".
Deferring it would have left `X-04` permanently unacceptable. **A task named in another task's
acceptance criteria is not optional.** `triage.py` reports this automatically.

**2. The silently-wrong test.** Does deferring it make output *wrong* rather than *absent*?

The SME sign-off on collapse decisions (`X-15`). Deterministic is not the same as correct:
normalisation strips signature pages and headers before hashing, so a rule one step too aggressive
merges two genuinely different agreements. Nothing else in the plan catches that. → Kept.

Same test keeps the no-op write guard (`X-09a`): without it an unchanged re-run silently re-embeds
the whole corpus. The system still answers; it just costs a fortune to run.

**3. The foundation test.** Does deferring it mean redoing work already done?

The document identity model. Changing `doc_id` after 50,000 documents are loaded means re-ingesting
all of them. Foundational work is cheapest before the thing it underpins exists, so it belongs
early even when nothing visible depends on it yet.

**4. The pair test.** Is it one half of a pair?

Defer both or neither. `X-05` + `X-06` and `S-09` + `F-02` are pairs; deferring one half leaves
either a control with nothing to control, or — far worse — a hazard with its control removed.
`triage.py` reports mutual and one-way rationale references; one-way is the common case.

**5. The blast-radius test.** Is it a risk mitigation or a piece of checklist evidence?

You may still defer it, but the risk then reads as mitigated when it is not, and the checklist line
asks for evidence nothing will produce. On one plan this left **two risks reading as controlled and
four unverifiable sign-off lines.** If you defer it, rewrite the risk and the checklist line in the
same change. `triage.py` scans the risk and checklist sheets for this.

---

## The trap: over-correction

The worst error of the reference engagement was cutting two different things because they shared a
label. "SME work" turned out to be two separate things:

| | What it was | Verdict |
|---|---|---|
| A **volume-driven review queue** — adjudicating every document in a 0.90–0.98 fuzzy-match band | grows with the corpus; only exists if fuzzy matching ships | correctly cut |
| A **fixed sample-based sign-off** — a human confirming the collapse decisions are right | fixed size; mandatory regardless of technique | wrongly cut, restored |

**Before cutting anything, separate why each part exists.** If one label covers two mechanisms,
split it and judge each separately. Ask specifically: *does this scale with the data, or is it a
fixed cost?* Volume-driven work is a candidate; a fixed gate usually is not.

---

## Ordering — what "critical first" actually means

Front-loading is not the same as doing the P0s first. Two rules matter more:

**Pull cheap gates forward, regardless of priority.** A 1.5-day task in front of 23.5 days of
dependent work belongs in week 1 — that is `D-14` (prove Drive access) and `Q-00` (prove the
dependency closure vendors). Both are small, neither is glamorous, and discovering a problem in
either one late strands everything queued behind it. `triage.py --spike-max 2 --chain-min 10`
reports these.

**Put foundations before the things they underpin, even with nothing visibly depending on them
yet.** See the foundation test above.

Everything else follows from the dependency graph, which the scheduler already honours.

---

## When you do defer, record six things

Move the row to a separate deferred section — never delete it. Each row keeps:

1. **What it was** — ID, title, original priority and phase
2. **Days** it removed from the plan
3. **Why it is deferred** — which of the five DEFER patterns applies
4. **Why it was needed for production** — the original argument, unedited
5. **Work required and acceptance criteria** — the full original analysis, so it can return without
   re-deriving it
6. **The RULE**, if it is half a pair, written beside both rows

Then re-run `validate.py`, which sweeps every other sheet for references to what you just deferred.

---

## Set expectations honestly

**Deferral is scope discipline, not a schedule lever.** On the reference plan, cutting 24.5 days of
scope bought **0.7 weeks**, while re-levelling work across seats bought **2.7 weeks** with no cut at
all. Defer to deliver value earlier and to keep the plan honest about what production requires — not
to hit a date. For duration, run `schedule.py --scenarios`.

And expect the shortlist to shrink under scrutiny. Of nine tasks deferred on the reference plan,
three were later restored once the tests above were applied properly. **A candidate list is a
starting point for judgement, not a decision.**

---

## Running it

```bash
python3 __SKILL_DIR__/triage.py --backlog PLAN.xlsx

# widen the de-risking sweep: any task ≤3d gating ≥8d of work
python3 __SKILL_DIR__/triage.py --backlog PLAN.xlsx --spike-max 3 --chain-min 8
```

Read the tiers in this order — `CANNOT DEFER` first so you know what is load-bearing, then
`ENHANCEMENT CANDIDATES` for the real shortlist. Treat `ASSURANCE LEAVES` as a warning, not scope:
tests, runbooks, penetration testing and sign-off have no dependents **by nature**, and every one of
them is required.
