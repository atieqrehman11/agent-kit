# deliver — maintainer notes

Why this is a skill and not a set of agents, and what would break if you changed that.

## Why no implementer subagent

`STANDARD.md` §1.1 promotes a capability to subagent only if it earns one of context economy,
independence, or fan-out. Implementation earns none:

- **Context economy** — it produces a diff and needs the design, the standards and the
  surrounding code. It reads a lot *and* writes a lot. No saving.
- **Independence** — actively harmful. The implementer *should* be anchored to the design it
  just produced. Independence is the product for a reviewer, not a builder.
- **Fan-out** — one feature is one chain. Fan-out only appears across several independent
  features, which is what the adapter-level wrapper handles.

`reviewer` and `qa` do earn it, on independence and context economy respectively. They already
exist. This skill is the sequencing that was missing, not new workers.

## Why the gates are in a reference file

`SKILL.md` is loaded whenever the model considers the skill. `reference/gates.md` is read once
the skill is actually running. Putting the exit conditions in the reference keeps the
selection-time cost small while making the contract available where it is used.

## The three load-bearing rules

Everything else is scaffolding around these:

1. **Bounded fix loop (3 rounds).** Without a bound, an unsupervised run can alternate between
   two fixes indefinitely. The bound is what makes it safe to walk away. `BLOCKED` is a
   first-class outcome, not a failure of the skill.
2. **Verbatim review.** The moment the running agent is allowed to summarise the review, the
   review stops being independent — it gets filtered through the context that produced the
   code. Verbatim is the whole mechanism.
3. **Pasted test output.** "Tests pass" is unfalsifiable from a report. The output is not.

Weaken any of the three and the skill still appears to work, which is the problem — it fails
silently, on the runs nobody watched.

## What it deliberately does not do

Push, open a pull request, deploy, migrate a shared environment, rotate a credential, or edit
CI. Those reach past the repo, and an unsupervised run is precisely when nobody is watching.
The deliverable is a local branch plus a report.

## Relationship to the adapter wrapper

Running several independent requirements at once, in isolated worktrees, with a notification
on completion, is tool-shaped and lives in the adapter (`adapters/claude/workflows/`). The
gate logic stays here so a second adapter gets it for free. Keep it that way: if a gate ever
needs to know how it is being orchestrated, the split is wrong.
