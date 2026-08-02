---
name: deliver
kind: skill
description: >
  Take a stated requirement through spec and into reviewed, tested code: acceptance criteria,
  a coverage pass for what is missing, design, a task list, implementation against the repo's
  standards, an independent review, a bounded fix loop, tests, and a written report. Run it
  supervised, stopping for approval on each document before any code exists, or unsupervised
  end to end. Use when you know what you want built. For planning, estimating or scheduling a
  release rather than building one feature, use the plan skill.
version: 2.0
arguments: "[the requirement, in your own words — or the slug of a spec already written]"
---

# Deliver

Run one requirement through nine gates to reviewed, tested code, and report back.

The gates exist because work fails in predictable places: it drifts from what was asked, it
misses the part nobody thought of, it reviews itself, and it stops at "looks done". Each gate
has a **binary exit condition**. You do not pass a gate by judging that it went well.

> **Read [`reference/gates.md`](__SKILL_DIR__/reference/gates.md) now.** It holds the exit
> condition, the failure mode and the stop rule for each gate, plus the load-or-derive and
> staleness rules. This file is the map; that file is the contract.

## Two commands, one artifact contract

| | Gates | Stops for approval | Writes code |
|---|---|---|---|
| {{cmd:deliver:spec}} | 0 → 3 | after each document | no |
| {{cmd:deliver:feature}} | 0 → 8 | no | yes |

They are not a pipeline where one is a prefix of the other, and neither calls the other.
Both write the **same four files**, and both read any that already exist:

```
docs/specs/<slug>/
  requirements.md    gate 0
  design.md          gate 2
  tasks.md           gate 3
  report.md          gate 8
```

So `spec` then `feature` skips nothing and repeats nothing — `feature` finds three documents
already written and starts at Build. `feature` on its own derives those same three documents
as it goes and leaves them behind. Either way you can hand-edit `design.md` and re-run: the
edit is the input.

## When to run this instead of something else

| Situation | Use |
|---|---|
| You want the plan right before it is built | {{cmd:deliver:spec}}, then {{cmd:deliver:feature}} |
| You know the requirement and want the finished, reviewed result | {{cmd:deliver:feature}} |
| You want to explore, or the requirement is still forming | ordinary conversation |
| You want a schedule, estimate or backlog across many features | {{cmd:plan:release}} |
| You want a new repo rather than a change to one | {{cmd:scaffold:new}} |

`{{cmd:plan:release}}` and this skill compose **vertically, not nested**: a release plan
produces a backlog, and each backlog item becomes one spec-and-deliver run. Gate 3 here
borrows the plan skill's definition of a well-formed task so the two agree, but it does not
call into it — priority, estimates, dependencies and scheduling are release-scope ceremony
that one feature does not need.

## The gates

```
0  Frame     requirement → numbered binary criteria + coverage pass  → requirements.md   DOC
1  Ground    repo type, standards, test and lint commands            → context           CTX
2  Design    assumptions, options, recommendation, risks             → design.md         DOC
3  Tasks     dependency-ordered, files named, every AC covered       → tasks.md          DOC
4  Build     implement against those standards, on a branch          → every AC has code
5  Review    the reviewer subagent, in its own context               → VERDICT verbatim
6  Fix       bounded loop — at most 3 rounds                         → PASS, or STOP
7  Test      the qa subagent, then run the tests                     → output pasted
8  Report    write the report file                                   → report.md         DOC
```

**Gates are ordered and you may not skip forward.** A design that follows the code is a
justification, not a design.

A `DOC` gate whose file already exists is **loaded, not re-run**. The `CTX` gate always runs —
its output is guidelines in your context, and context does not persist.

## Rules that make it safe to leave alone

1. **Work on a branch.** Never commit to the default branch. Create `deliver/<slug>` before
   gate 4 and stay on it. Do not push and do not open a pull request unless the user asked
   for one — finishing on a local branch is the deliverable.
2. **The fix loop is bounded at 3 rounds.** On a fourth FAIL, stop and report the unresolved
   findings. An unsupervised loop that cannot converge must halt, not keep spending. Report
   the block as the outcome — a stopped run that says why is a success of this skill, not a
   failure.
3. **You do not review your own work.** Gate 5 is the `reviewer` subagent, in a fresh context.
   Its verdict goes in the report **verbatim**, including anything unflattering. The same
   logic puts a fresh-context coverage pass inside gate 0.
4. **Never weaken a test or a criterion to reach green.** If a criterion turns out to be
   wrong, say so in the report and leave it failing.
5. **Report honestly.** If tests fail, paste the failure. If you skipped something, name it.
   A report that overstates what was delivered is worse than no report — the whole point of
   running unsupervised is that the report is the only thing the user reads.
6. **Stop and ask** only when proceeding under either reading would produce work that has to
   be thrown away. Otherwise state the assumption and continue. `spec` is the exception by
   design: its stops are the product, not an escalation.

## Scope boundaries

Do not, without being asked: push a branch, open a pull request, deploy, run a migration
against a shared environment, rotate a credential, or change CI configuration. These are the
actions whose blast radius extends past the repo, and an unsupervised run is exactly when
nobody is watching.

## Output

`spec` ends with the folder path and a handoff line. `feature` ends with the path to the
report, plus a five-line summary in chat: verdict, criteria met, tests, what is left, and
what was assumed. Everything else lives in the files —
[`templates/`](__SKILL_DIR__/templates/).
