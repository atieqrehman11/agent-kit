# TPLVAR_ID — Tasks

Source of truth for the work. Every number reported anywhere else derives from this table.

**Columns are read by header name, never by position** — reorder them freely.

- `ID` — `<REPO-PREFIX>-NN`, e.g. `API-01`. Split a task along a real seam with `a`/`b`
  suffixes (`ETL-03a`, `ETL-03b`), never by rounding it down.
- `Repo` — MUST match a repo listed in `spec.md` § Repos Touched.
- `Covers` — requirement IDs from `spec.md`, comma-separated. `-` only for pure enabling
  work (CI, access requests) that no requirement names directly.
- `Days` — one person, hands-on-keyboard. Excludes review latency and waiting. **Max 5.**
  Anchors: `0.5` config change with a test · `1` contained code change · `2` small feature
  with tests · `3` feature across two layers · `5` a subsystem.
- `Priority` — `P0` blocker for the stated end state · `P1` required for go-live ·
  `P2` required soon after · `P3` deferrable.
- `Depends` — task IDs, comma-separated, or `-`. Decisions block too: write `D-01`.
- `Status` — `TODO` · `WIP` · `DONE` · `BLOCKED`.

| ID | Repo | Task | Covers | Days | Priority | Depends | Status |
|---|---|---|---|---|---|---|---|
TPLVAR_TASK_ROWS

## Deferred

Cut scope, kept with its full reasoning so it can return without redoing the thinking.

If task B existed only to contain task A's risk, deferring A makes B pointless — but
reinstating A without B is dangerous. Write that RULE beside both rows.

| ID | Task | Days | Why deferred | RULE |
|---|---|---|---|---|
