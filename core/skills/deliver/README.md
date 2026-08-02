# deliver — maintainer notes

Why this is a skill and not a set of agents, why it has two commands rather than one, and
what would break if you changed either.

## Why two commands and not a flag

`spec` and `feature` differ on the one axis a flag handles badly: whether stopping is the
product. `feature` rule 6 says *do not stop, assume and continue* — that is the contract that
makes it safe to walk away from. `spec` exists to stop three times. A `--supervised` flag
would put a rule and its own negation in the same file, and the model would have to work out
which applies. Two entry points, one shared `reference/gates.md`, is the cheaper split.

They do not call each other. Composition happens through the **files**, not through control
flow — see below.

## Why load-or-derive instead of nesting spec inside feature

The obvious design is `feature` invoking `spec` internally and skipping it when a spec
exists. It was rejected because it answers the wrong question. Gates do not differ by *who
ran them*; they differ by **what they leave behind**:

| Class | Example | Second run |
|---|---|---|
| document | gate 0, 2, 3, 8 | load the file |
| context | gate 1 Ground | always re-run — nothing persisted |
| code | gates 4–7 | `feature` only |

Once that is the rule, the redundancy question dissolves: `feature` reads
`docs/specs/<slug>/<doc>.md` if it exists and derives-and-writes it if it does not. Nesting
would express the same skip with an extra layer, plus an unanswerable question about whether
the nested call stops for approval.

The consequence worth protecting: **a document is identical whichever command produced it.**
That is what makes a run resumable — hand-edit `design.md`, re-run `feature`, and the edit is
the input. Break the artifact contract and you lose resume, which is the feature that makes
iteration cheap.

`derived-from: <upstream>@<hash>` exists for the failure this opens up. Without it, editing
`requirements.md` after `design.md` was approved silently builds against a stale design.
`git hash-object` is used rather than a commit sha because specs are edited before they are
committed.

## Why the specs live in the repo, in a visible `docs/`

Three mechanical reasons, none of them preference:

1. **It diffs.** A design change shows up in review next to the code implementing it. That
   alone kills most spec rot.
2. **It is inside the enforcement blast radius.** The guidelines' `applies_to` globs and the
   `reviewer` subagent operate on the repo tree. A spec in a wiki is invisible to every
   mechanism this kit has.
3. **Not a dot-directory.** Hidden folders are a reasonable choice for a tool that surfaces
   them in its own UI. Nothing here does, so hiding them means nobody reads them.

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

### The coverage pass is an open promotion question

Gate 0's coverage pass earns **independence** by the same argument gate 5 does — whoever wrote
the criteria is the worst judge of what they forgot. By the promotion test it should be a
third subagent, not a fresh-context pass described in prose.

It is not one yet, deliberately: it reads very little (a requirement and a criteria list), so
context economy does not apply, and a subagent that exists only for independence on ~40 lines
of input is a round trip for a small return. If it proves its worth, promote it to
`core/subagents/critic.md` and have gate 0 dispatch it by name. Leaving it as prose is the
weaker form and should not be mistaken for the settled answer.

## Why the gates are in a reference file

`SKILL.md` is loaded whenever the model considers the skill. `reference/gates.md` is read once
the skill is actually running. Putting the exit conditions in the reference keeps the
selection-time cost small while making the contract available where it is used.

Both commands read the same reference. If a gate's rule ever needs to differ by command, that
is a signal the split is in the wrong place — the difference should be in the command file,
and the gate should stay one thing.

## The load-bearing rules

Everything else is scaffolding around these:

1. **Bounded fix loop (3 rounds).** Without a bound, an unsupervised run can alternate between
   two fixes indefinitely. The bound is what makes it safe to walk away. `BLOCKED` is a
   first-class outcome, not a failure of the skill.
2. **Verbatim review.** The moment the running agent is allowed to summarise the review, the
   review stops being independent — it gets filtered through the context that produced the
   code. Verbatim is the whole mechanism.
3. **Pasted test output.** "Tests pass" is unfalsifiable from a report. The output is not.
4. **A `spec` stop shows the exclusions and the least-certain item, not just the document.**
   A checkpoint that asks "approve?" over a clean-looking artifact manufactures agreement —
   the reviewer can only react to what was thought of, and the gap is never there.
5. **Gate 3 has no estimates.** The moment tasks carry days, this becomes a worse version of
   `plan:release` and inherits its ceremony. The boundary is: plan owns priority, estimates,
   dependencies across features, and schedule; deliver owns one feature's dependency order.
   Gate 3 borrows plan's *definition* of a well-formed task so the two agree, and nothing else.

Weaken any of these and the skill still appears to work, which is the problem — it fails
silently, on the runs nobody watched.

## What it deliberately does not do

Push, open a pull request, deploy, migrate a shared environment, rotate a credential, or edit
CI. Those reach past the repo, and an unsupervised run is precisely when nobody is watching.
The deliverable is a local branch plus the spec folder.

## Relationship to the adapter wrapper

Running several independent requirements at once, in isolated worktrees, with a notification
on completion, is tool-shaped and lives in the adapter (`adapters/claude/workflows/`). The
gate logic stays here so a second adapter gets it for free. Keep it that way: if a gate ever
needs to know how it is being orchestrated, the split is wrong.
