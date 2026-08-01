---
name: diagram
kind: skill
description: >
  Build a new draw.io diagram, or audit an existing one, with a mandatory
  check → render → read loop before it is shown to anyone. Use for architecture,
  network, data-flow, auth topology and ERD diagrams, and whenever a .drawio file
  is created, edited or reviewed.
requires:
  bin: [drawio]
---

# Diagram

Never present a diagram that has not been rendered to an image and looked at. Overlaps,
edges routed through boxes and clipped labels are invisible in the XML and obvious in
the PNG.

## Entry points

- `{{cmd:diagram:build}}` — create a diagram, then verify it
- `{{cmd:diagram:review}}` — audit a diagram that already exists

## Payload

- `reference/architecture.md` — layer layout, icon sets, connection and colour rules
- `reference/erd.md` — hub-and-spoke layout, atomic-column and cardinality rules
- `check.py` — geometric checks: overlaps, edge-over-node crossings, unlabelled edges
- `render.py` — export to PNG via the draw.io CLI

Follow the active project's brand guidance for palette and typography. This skill owns
diagram *structure*; it does not own colour.
