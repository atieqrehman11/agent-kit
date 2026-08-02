---
name: review
kind: command
description: >
  Audit an existing draw.io diagram — geometry checked deterministically, then rendered
  and looked at. Use before editing an inherited diagram, before shipping one into a
  document, or whenever someone asks whether a diagram looks right.
arguments: "[path to a .drawio file; default = choose from the repo]"
---

# Review an existing draw.io diagram

Audit a `.drawio` file the way it will be read: check the geometry deterministically, then
render it and look at it. Use this before editing an inherited diagram, before shipping one
into a document, or whenever someone asks "does this look right?".

## 1. Locate the file

If `{{args}}` names a file, review that. Otherwise list the candidates
(`ls **/*.drawio`, or the folder from `$DIAGRAMS_DIR` / the profile's `diagrams_dir`) and
ask which one. A multi-page file is reviewed one page at a time — `--page <n>`.

## 2. Check the geometry

```bash
python3 __SKILL_DIR__/check.py <file>.drawio          # --page N · --min-gap N · --json · --allow-unlabeled
```

Errors: **shape overlap**, **edge routed through a shape**, **unlabeled connection**.
Warnings: **crowding**, **no icons**. Exit code 1 means errors were found.

Two honest limits to report rather than paper over:
- Edge routing is checked as straight segments between the points draw.io stores, so a
  right-angle route can differ slightly from what the renderer draws — treat a reported
  crossing as a place to look.
- It is geometry only. It cannot tell you the diagram is on brand, correctly layered, or
  factually right about the system.

## 3. Render and read it

```bash
python3 __SKILL_DIR__/render.py <file>.drawio         # --scale · --page · --bin · --which
```

Read the PNG against the reference for its type —
[`reference/architecture.md`](reference/architecture.md) or
[`reference/erd.md`](reference/erd.md) — plus the project's brand guide
(`python3 __SKILL_DIR__/render.py --profile` → `brand_guidelines`, else the guide named
in the active project's instruction file; check the scope it reports actually belongs to
the project under review):

- [ ] Icons, not plain boxes, for major components; consistent sizing
- [ ] Layered/hub layout as the reference prescribes, in one consistent direction
- [ ] Every connection labeled (protocol/flow, or crow's-foot cardinality on an ERD)
- [ ] PK/FK marked and columns atomic (ERD)
- [ ] Brand palette and typography; 40–60px whitespace; grid-aligned
- [ ] Legend wherever color or line style carries meaning
- [ ] Content matches the real system — no invented components or connections

## 4. Report

Give a short verdict — **clean**, **fixable faults**, or **rebuild** — then the findings,
most severe first: each one as the file/shape it affects, what is wrong, and the fix. Group
the deterministic findings (from `check.py`) separately from what you found by reading the
render, so it is clear which are measured and which are judgment.

Offer to fix them with `{{cmd:diagram:build}}`, which rebuilds via a script and re-runs this loop.
Do not edit large XML by hand.
