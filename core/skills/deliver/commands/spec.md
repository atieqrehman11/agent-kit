---
name: spec
kind: command
description: >
  Turn an idea into an approved spec before any code exists — acceptance criteria, a coverage
  pass for what is missing, a design, and a task list, each written to a file and each
  stopping for your approval. Use when you want to be sure the plan is right before it is
  built; run the feature command afterwards to implement it. Writes documents, never code.
arguments: "[the idea, in your own words — or the slug of a spec already started]"
---

# Spec a feature

The input:

```
{{args}}
```

If that is empty, ask what to spec and stop.

If it names an existing `docs/specs/<slug>/`, this is a resume: read what is there and start
at the first document that is missing or `status: draft`. Otherwise it is an idea, and you
start at gate 0.

## What this command is

Gates **0 → 3** of [`../reference/gates.md`](__SKILL_DIR__/reference/gates.md), supervised.
Read that file now; it holds the exit condition for each gate and the load-or-derive and
staleness rules that make a resume safe.

```
0  Frame     requirements.md   → STOP for approval
1  Ground    context only      → no stop; it produces no document
2  Design    design.md         → STOP for approval
3  Tasks     tasks.md          → STOP for approval
```

**This command writes no code and creates no branch.** It stops after gate 3. Implementation
is {{cmd:deliver:feature}}, which will read these three documents rather than re-deriving
them.

## How to stop for approval

A checkpoint that only asks *"approve?"* manufactures agreement — the user approves a
document whose hole they had no way to see. So each stop presents four things, in this
order, and then asks:

```
── Gate 0 · Frame ─────────────────────────────
Written    docs/specs/<slug>/requirements.md

Exit condition
  <the gate's exit condition, and whether it is met>

Deliberately excluded
  <what a broader reading would have included, and why it is out>

Least certain
  <the single item here most likely to be wrong, and what it would cost>

Approve, or tell me what to change.
```

The **deliberately excluded** and **least certain** lines are the load-bearing ones. Without
them a checkpoint reviews only what you thought of, which is never where the gap is.

On approval, set `status: approved` in the document's front matter and move to the next gate.
On a change request, edit the document, re-present, and ask again — do not carry the change
forward as an unwritten understanding.

## Rules

1. **Do not run ahead.** Do not draft the design while waiting for approval on the
   requirements. The point of the stop is that the next gate's input can still change; work
   done in advance becomes an argument for the version you already wrote.
2. **The coverage pass at gate 0 is not optional**, and it must not see your reasoning — only
   the requirement and the criteria. It exists because whoever wrote the criteria is the worst
   available judge of what they forgot. Its findings become criteria or stated exclusions;
   they may not be dismissed silently.
3. **Stamp every derived document** with `derived-from: <upstream>@<hash>`
   (`git hash-object`, first 12 chars). Before loading a document on a resume, recompute its
   upstream's hash — on a mismatch, stop and say which two files disagree.
4. **Ask, do not assume, at a stop.** Between stops the ordinary rule applies: assume, label
   it `A1`, `A2`, and carry on. At a stop, the open assumptions are part of what you present.
5. **No estimates, no priorities, no schedule.** Those are {{cmd:plan:release}}'s nine gates,
   and running them for one feature is ceremony. Gate 3 produces a dependency-ordered task
   list and nothing more.

## Finish

After gate 3 is approved, return the folder and the handoff line — nothing else:

```
Spec      docs/specs/<slug>/          requirements · design · tasks
Criteria  n, of which n are negative-path
Tasks     n, in m dependency layers
Assumed   the assumption that would most change the build if wrong
Next      {{cmd:deliver:feature}} <slug>
```
