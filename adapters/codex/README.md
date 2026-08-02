# Codex adapter — PARKED

There is **no installer here yet**. What survives from the pre-existing Codex material is
the hand-written [`AGENTS.md`](AGENTS.md). The `skills/` directory this file used to
describe — nine personas in Codex's own layout — was the source material for the three
kinds in `core/` and was removed once they landed; it is in the git history if needed.

Building this adapter is deferred work, tracked as **A-03** in
[`../../CONSOLIDATION-PLAN.md`](../../CONSOLIDATION-PLAN.md). What it needs to do is
already specified — see [`../../STANDARD.md`](../../STANDARD.md) Part 2. In particular
§2.2 lets an adapter support only some of the three kinds, provided it logs by name
whatever it skipped, so Codex can ship partial without changes to `core/`.

Two things the spec has gained since this was parked, both of which A-03 must handle:

- **Conformance siblings** (§1.2). `core/guidelines/<name>.conformance.md` is payload of the
  guideline beside it — install it, never register it, and fail on one whose guideline is
  missing. Discovering it as an artifact in its own right derives the name
  `service-structure.conformance`, which matches no frontmatter and fails obligation 2.
- **Marker resolution is a general scan** (§1.6, obligation 5). Resolve every `__TOKEN__`,
  and verify by scanning for *any* surviving `__[A-Z_]+__` rather than a list of the ones you
  remembered. The Claude adapter checked three known names and shipped `__ORG_PREFIX__`
  into six installed guidelines for as long as that list existed.
