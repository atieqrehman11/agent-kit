# Specs

One folder per feature. The spec is written **before** the code and committed **with** it, so
a design change shows up in review next to the change it caused.

```
docs/specs/<feature-slug>/
  requirements.md    numbered, binary acceptance criteria + what is deliberately excluded
  design.md          assumptions, options and trade-offs, risks, files, AC coverage
  tasks.md           dependency-ordered tasks, files named, every AC covered
  report.md          written after the build: verdict, evidence, review, test output
```

## How they get written

| | |
|---|---|
| {{cmd:deliver:spec}} | writes the first three, stopping for your approval after each. No code. |
| {{cmd:deliver:feature}} | builds it — reading any document that already exists, deriving and writing any that does not, then adding `report.md`. |

So the two compose without repeating work: run `spec` when you want the plan right first, run
`feature` alone when you do not, and you get the same four files either way.

## The two rules that keep them honest

1. **Every document is stamped with the content hash of the one above it**
   (`derived-from: requirements.md@<hash>`). Edit `requirements.md` after `design.md` was
   written and the mismatch is caught, rather than silently building against a stale design.
2. **The report does not restate the spec.** It references criteria and decisions by number
   and records only what the build learned — including where it diverged from the design.

## Reviewing one

The sections most worth your attention are the ones that are easy to skim past:

- **Explicitly not doing** in `requirements.md` — the difference between a scope decision and
  an oversight.
- **The critic table** — findings from an independent pass that read the code looking only for
  what is missing: failure modes, non-functional constraints, integration points, unstated
  premises, lifecycle, boundaries, observability. Each must resolve into a criterion or a
  stated exclusion, and `VERDICT: COMPLETE` is only meaningful next to the *checked and clean*
  line that says which dimensions were actually examined.
- **Unglamorous work** in `tasks.md` — migrations, config, fixtures, error paths, docs. "None"
  there is a claim, not a default.

Delete this file if the convention does not suit the repo; nothing depends on it existing.
