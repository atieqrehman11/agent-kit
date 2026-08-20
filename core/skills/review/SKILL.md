---
name: review
kind: skill
description: >
  Review a pushed change — a merge request, or a branch — against the standards its changed
  files actually trigger. Resolves the diff, derives which guidelines apply from their own
  applies_to globs, dispatches one independent reviewer per surface, and consolidates into a
  single verdict. Use when asked to review an MR, a merge request, or a branch that is already
  pushed. An uncommitted working diff is reviewed directly instead — this skill is for a change
  with a base to diff against.
requires:
  bin: [glab]
---

# Review

Five steps, in order. **Step 2 is the one that must not be skipped** — a reviewer that infers its
own standards produces a different result each run, which is the whole failure this skill exists
to remove.

## 1. Resolve what is being reviewed

Four things must be right before anything else happens, and every one of them fails silently
while still producing a confident-looking review.

**The base is a remote ref, never a local branch name.**

```
git fetch origin <target> refs/merge-requests/<id>/head
git diff origin/<target>...FETCH_HEAD
```

Measured on a real repo while this skill was being written: a local `main` four commits stale
reported **3 changed files for an already-merged merge request**. Against `origin/main` the same
MR correctly diffed to zero. A stale checkout is the normal state of any repo nobody is actively
working in, so this is the default failure, not an edge case. Fetching the MR without creating a
local branch also leaves nothing to clean up and cannot collide with an existing branch.

**Three dots, not two** — the base is then the merge base, so the diff holds only this change's
own commits rather than everything the target gained since.

**Read state and target from the API** when the forge CLI is authenticated: `state`,
`source_branch`, `target_branch`, `title`, `description`. A `merged` or `closed` merge request has
nothing left to review — say so and stop.

Without an authenticated CLI, discover and assume:

```
git ls-remote origin 'refs/merge-requests/*/head'      # ids, but not their state
git ls-remote --symref origin HEAD                     # the default branch
```

The target is then the default branch and **the scope line says `(assumed)`**. State is unknowable
this way — which is exactly why the next rule exists.

**An empty diff is a result, not an error.** Report it and stop: no reviewer is dispatched, and
never switch to a two-dot diff to manufacture content. If the API says the MR is open and the diff
is still empty, the target branch is wrong — fix that before anything else.

**If the fetch fails, stop and say why.** Never fall back to the working tree; that reviews the
wrong change under the merge request's name.

## 2. Derive which standards apply

Read the `applies_to` globs from the frontmatter of each guideline in `__GUIDELINES_DIR__` and
match them against the changed-file list.

**Do not keep a mapping of repositories to standards.** The globs are the mapping. A second copy
drifts, and a name-based map breaks on the first rename.

Then apply the additions in `__SKILL_DIR__/reference/detection.md` — what a glob cannot express,
including the LLM-call detection that decides whether `python-llm` is in scope, and the rule that
routes a repo's `python/` build and deploy scripts to the surface they deploy rather than to
generic Python.

Record the result as an explicit list. Every reviewer is told its standards; none infers them.

## 3. Dispatch one reviewer per surface

Group the changed files by surface — front end, service, pipeline, job, agent, Genie space — and
dispatch the **`reviewer` subagent** once per group, in parallel, each in its own context.

Give each one:

- the diff **scoped to its own files**, and the base it was taken against
- the explicit list of guidelines that are its contract
- the instruction to read `__GUIDELINES_DIR__/conformance/<name>.md` for each, and to open the
  guideline itself only to quote a rule a finding breaks
- the MR title and description as stated intent, if available

One reviewer over the whole diff is the wrong shape: context dilutes, and the structure gate is
the first thing that gets skimmed.

## 4. Consolidate

Rules, in `__SKILL_DIR__/reference/detection.md`. The four that change the outcome:

- **Worst verdict wins.** One `FAIL` makes the review `FAIL`.
- **Drop any standards finding that does not cite its rule and its line.** The reviewer is
  already required to; enforcing it here is what stops a plausible invention surviving.
- **Dedupe by file and line**, keeping the more specific statement.
- **Merge the structure gates** per shape, worst verdict per row — the service table and the
  Databricks table stay separate, because their rows are different checks. A review can emit
  one, the other, or both.

## 5. Emit one review

Never post it. Print it, and offer to post — a comment on someone's merge request is
outward-facing and awkward to retract. Posting happens only when asked, and only with a forge
CLI that is authenticated.

Output shape:

```
VERDICT: PASS | PASS_WITH_CONDITIONS | FAIL

Scope     <guidelines applied> · base <target> (assumed, if it was) · <n> files, <n> surfaces
Summary   one paragraph

Structure gate      merged table(s) — service, Databricks, or both, per what was touched
Critical issues     must fix
Warnings            should fix
Suggestions         optional
Positive            what was done well

Fix prompt          only when the verdict is FAIL
```

The scope line is not decoration. It is how someone reading the review later knows which
standards were applied and which were guessed at.

## What this does not do

- **Approve, merge or post** without being asked.
- **Fix the code.** The fix prompt is the handoff; applying it is a separate deliberate step.
- **Re-review unchanged code.** A pre-existing violation in a file the diff merely touches is a
  warning naming the file, never a blocker.
