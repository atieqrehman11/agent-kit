---
name: build
kind: command
description: >
  Build a new draw.io diagram — architecture, network, data-flow, auth topology or ERD —
  and check, render and read it before it is shown to anyone. Use when a diagram is asked
  for, or a new .drawio file is created.
---

# Build a draw.io diagram with mandatory self-verification

Build a `.drawio` diagram — architecture, network, data-flow, auth, or ERD — that follows
the project's brand and is **already correct on the first version you show the user**. The
recurring failures this exists to prevent: plain boxes where icons belong, overlapping
shapes, relationship lines routed across tables, generic template styling, and unlabeled
connections.

Do **not** hand-present a diagram that has not been checked and rendered. The verify loop in
step 4 is not optional.

## 1. Establish context (before drawing)

- **Diagram type** → load the matching reference and follow it as the spec:
  - Architecture / network / data-flow / traffic / auth → [`reference/architecture.md`](reference/architecture.md)
  - Entity-relationship → [`reference/erd.md`](reference/erd.md)
- **Brand** → load the style guide this project's diagrams must follow, and never mix one
  project's brand into another's diagram. Resolve it in this order:
  1. a style guide the user names in this request,
  2. the `brand_guidelines` value in the profile governing this directory —
     `python3 __SKILL_DIR__/render.py --profile`, which prints the values **and** the
     scope they came from. A `global` scope while you are inside one client's tree is
     how another client's palette reaches this diagram: check the value names the brand
     you are actually drawing for before you use it,
  3. the style/brand guide the active project's instruction file points at,
  4. no brand guide → use the reference file's own defaults and say so when presenting.
- **Output folder** → a design/docs workspace, never a deployed code repo. Resolve:
  `$DIAGRAMS_DIR` > profile `diagrams_dir` > the folder the user names > the project's
  existing diagrams folder (find it: `ls **/*.drawio`). If the only candidate is a
  deployed application repo, stop and ask — that is the wrong destination.
- **Content** → what actually exists. Read the code, configs, and docs you are diagramming;
  do not invent components or infer a topology from the diagram type.

## 2. Build via a script, not by hand

Generate the XML with a small Python script rather than hand-editing large XML — it is far
more reliable for spacing, alignment, and avoiding overlaps, and it makes the next revision
cheap. Write the script to a scratch location, not into the user's project.

draw.io stores HTML in the `value` attribute **escaped**: use `&#10;` for line breaks and
escape the text — never embed raw `<tag>` markup.

Use real icons (`shape=mxgraph.*`, `image=…`) for major components; a diagram of plain
rectangles is the single clearest sign of generated output.

## 3. Check the geometry (deterministic)

```bash
python3 __SKILL_DIR__/check.py <file>.drawio          # add --allow-unlabeled for a plain sequential flow
```

It reports, as errors: **shape overlap**, **edges routed through shapes**, and **unlabeled
connections**; as warnings: **crowding** (< 20px gaps, tune with `--min-gap`) and **no
icons**. Fix and re-run until it exits clean. This is geometry only — it cannot judge
whether the diagram reads well, which is what step 4 is for.

## 4. Render and SELF-REVIEW (the required loop)

```bash
python3 __SKILL_DIR__/render.py <file>.drawio         # --scale, --page, --bin available
```

The binary is resolved from `--bin` > `$DRAWIO_BIN` > profile `drawio_bin` > `PATH` > the
usual install locations; `--which` prints what would be used. If no draw.io is installed,
say so and deliver only after the user has an alternative way to view it — do not present an
unrendered diagram as verified.

**Read the PNG** and check every item. Re-generate and re-render until all pass:

- [ ] **Icons, not boxes** — major components use real service/stencil icons, consistently sized (40–60px).
- [ ] **No overlap** — no two shapes overlap (nesting inside a container is fine).
- [ ] **No edge-over-shape** — connections never cross a shape they do not touch.
- [ ] **Every connection labeled** — protocol/flow on architecture edges; crow's-foot + 1:1 / 1:N on ERD edges, PK/FK marked.
- [ ] **Layout matches the reference** — architecture: labeled layers in one consistent direction with actors at the consumption end; ERD: compact grouped hub with radiating satellites, one atomic column per row.
- [ ] **On brand, not generic** — correct palette and typography, 40–60px whitespace, aligned to grid. No default blue boxes, no rainbow autoshapes, no clip-art.
- [ ] **Legend** present whenever custom colors or line styles carry meaning.
- [ ] **Content is true** — every component and connection exists in the system being described.

State the checklist result to yourself; only proceed once it is clean.

## 5. Present

Save the `.drawio` to the resolved output folder, then show the user the rendered PNG and
the file path. Name which checklist items you corrected between versions, so the fix history
is visible. Never deliver only the XML.

## Notes

- **Editing an existing diagram?** Run `{{cmd:diagram:review}}` on it first — fix what it finds
  before layering new content onto an already-broken layout.
- **File naming:** `{sequence}-{component}-{version}.drawio`, e.g. `03-network-topology-v3.drawio`.
- **Nothing here is machine-specific.** Output folder, brand guide, and draw.io binary all
  come from the profile or the environment; set them once in the shared profile sheet and
  apply with `{{cmd:scaffold:profile}}`.
