---
name: deliver
kind: skill
description: >
  Take a stated requirement all the way to reviewed, tested code without supervision:
  acceptance criteria, design, implementation against the repo's standards, an independent
  review, a bounded fix loop, tests, and a written report. Use when you know what you want
  built and want to be handed the finished result plus its review, rather than driving each
  step. For planning or estimating instead of building, use the plan skill.
version: 1.0
arguments: "[the requirement, in your own words]"
---

# Deliver

Run one requirement through seven gates to reviewed, tested code, and report back.

The gates exist because unsupervised work fails in predictable places: it drifts from what
was asked, it reviews itself, and it stops at "looks done". Each gate has a **binary exit
condition**. You do not pass a gate by judging that it went well.

> **Read [`reference/gates.md`](__SKILL_DIR__/reference/gates.md) now.** It holds the exit
> condition, the failure mode and the stop rule for each gate. This file is the map; that
> file is the contract.

## When to run this instead of just building

| Situation | Use |
|---|---|
| You know the requirement and want the finished, reviewed result | **this skill** |
| You want to explore, or the requirement is still forming | ordinary conversation |
| You want a schedule, estimate or backlog | `{{cmd:plan:release}}` |
| You want a new repo rather than a change to one | `{{cmd:scaffold:new}}` |

## The gates

```
0  Frame        requirement → numbered, binary acceptance criteria      → user confirms if ambiguous
1  Ground       identify the repo type and load its standards           → standards named in the report
2  Design       assumptions, options, recommendation (design guideline) → recorded, not narrated
3  Build        implement against those standards                       → every criterion has code
4  Review       the reviewer subagent, in its own context               → VERDICT recorded verbatim
5  Fix          bounded loop — at most 3 rounds                         → PASS, or STOP and report
6  Test         the qa subagent, then run the tests                     → output pasted, not summarised
7  Report       write the report file                                   → path returned to the user
```

**Gates are ordered and you may not skip forward.** A design that follows the code is a
justification, not a design.

## Rules that make it safe to leave alone

1. **Work on a branch.** Never commit to the default branch. Create
   `deliver/<slug>` before gate 3 and stay on it. Do not push and do not open a pull
   request unless the user asked for one — finishing on a local branch is the deliverable.
2. **The fix loop is bounded at 3 rounds.** On a fourth FAIL, stop and report the
   unresolved findings. An unsupervised loop that cannot converge must halt, not keep
   spending. Report the block as the outcome — a stopped run that says why is a success of
   this skill, not a failure.
3. **You do not review your own work.** Gate 4 is the `reviewer` subagent, in a fresh
   context. Its verdict goes in the report **verbatim**, including anything unflattering.
4. **Never weaken a test or a criterion to reach green.** If a criterion turns out to be
   wrong, say so in the report and leave it failing.
5. **Report honestly.** If tests fail, paste the failure. If you skipped something, name it.
   A report that overstates what was delivered is worse than no report — the whole point of
   running unsupervised is that the report is the only thing the user reads.
6. **Stop and ask** only when proceeding under either reading would produce work that has to
   be thrown away. Otherwise state the assumption in the report and continue.

## Scope boundaries

Do not, without being asked: push a branch, open a pull request, deploy, run a migration
against a shared environment, rotate a credential, or change CI configuration. These are the
actions whose blast radius extends past the repo, and an unsupervised run is exactly when
nobody is watching.

## Output

The last thing you produce is the path to the report, plus a five-line summary in chat:
verdict, criteria met, tests, what is left, and what you assumed. Everything else lives in
the file — [`templates/report.md.tmpl`](__SKILL_DIR__/templates/report.md.tmpl).
