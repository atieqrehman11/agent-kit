# diagram

A Claude Code skill for producing `.drawio` diagrams that are **verified before they are
shown** — architecture, network, data-flow, auth, and ERDs.

| Command | What it does | Direction |
|---|---|---|
| [`{{cmd:diagram:build}}`](commands/build.md) | Build a diagram from the reference spec + the project's brand, then check, render, and self-review it. | system → `.drawio` + PNG |
| [`{{cmd:diagram:review}}`](commands/review.md) | Audit an existing `.drawio`: geometry check + rendered read-through + verdict. | `.drawio` → findings |

## Why it exists

Generated diagrams fail in the same few ways every time: plain boxes where service icons
belong, overlapping shapes, relationship lines routed straight across a table, unlabeled
connections, and default-template styling. Three of those are measurable, so they are
measured — not eyeballed.

```
build via script  →  check.py (geometry, deterministic)  →  render.py (PNG)  →  read it  →  present
                          ↑                                                        │
                          └────────────────── fix and repeat ─────────────────────┘
```

## The scripts

| Script | What it does |
|---|---|
| `check.py` | Lints the XML: shape overlap, edges routed through shapes, unlabeled connections (errors); crowding, no icons (warnings). Handles multi-page and compressed files. Exit 1 on errors. |
| `render.py` | Exports a PNG via the draw.io desktop binary so the diagram can actually be looked at. |

```bash
python3 check.py  diagram.drawio            # --page N · --min-gap N · --allow-unlabeled · --json
python3 render.py diagram.drawio            # --scale · --page · --transparent · --bin · --which
```

`check.py` is geometry only — it cannot judge whether a diagram is on brand, correctly
layered, or true to the system. That is what the rendered read-through in each command is
for, and neither command lets you skip it.

## References

`reference/architecture.md` and `reference/erd.md` are the specs the commands build against:
icon sets, layering, routing rules, cardinality notation, atomic columns, anti-patterns.
They carry structural rules and style *defaults* — wherever a project has its own brand
guide, that guide wins.

## Configuration

Nothing is machine- or project-specific in this skill. Each value is resolved at run time,
and every one is optional:

| What | Resolution |
|---|---|
| Output folder | `$DIAGRAMS_DIR` > profile `diagrams_dir` > the folder named in the request > the project's existing diagrams folder |
| Brand guide | named in the request > profile `brand_guidelines` > the guide the active `CLAUDE.md` points at > reference defaults |
| draw.io binary | `--bin` > `$DRAWIO_BIN` > profile `drawio_bin` > `PATH` > the usual install locations for the OS |

Set the profile values once in the shared profile sheet and apply them with
`{{cmd:scaffold:profile}}`; the fields are declared in this skill's `profile_fields.py`.

## Files

```
diagram/
  build.md        build + verify command
  review.md       audit-an-existing-diagram command
  check.py        deterministic geometry linter
  render.py       draw.io PNG export (binary resolved at run time)
  profile_fields.py               the profile fields this skill owns
  reference/architecture.md       architecture / network / data-flow / auth spec
  reference/erd.md                entity-relationship spec
```

---

See the top-level [README](../../README.md) for install instructions.
