# The nine gates

One section per gate: what you do, the **binary** exit condition, the failure mode it exists
to prevent, and when to stop.

A gate's exit condition is checkable by someone who was not watching. "The design is good" is
not an exit condition. "Every acceptance criterion appears in the design" is.

---

## What each gate produces, and what that means on a second run

Gates differ in what they leave behind, and that — not the command you ran — decides whether
a gate repeats.

| Gate | Produces | Class | On a run where it already exists |
|---|---|---|---|
| 0 Frame | `requirements.md` | **document** | load it |
| 1 Ground | loaded guidelines, test/lint commands | **context** | **always re-run** |
| 2 Design | `design.md` | **document** | load it |
| 3 Tasks | `tasks.md` | **document** | load it |
| 4 Build | code on a branch | code | — |
| 5 Review | a verdict | code | — |
| 6 Fix | code | code | — |
| 7 Test | tests and their output | code | — |
| 8 Report | `report.md` | document | written once, at the end |

**Gate 1 is context, not a document, and so it never counts as done.** `design.md` can *name*
which standards applied; naming them does not put the guideline text in front of whoever is
writing the code. Re-run it every time. It is cheap.

The three document gates resolve their input in this order — **first match wins**:

```
gate 0 / 2 / 3 input  =  docs/specs/<slug>/<doc>.md if present  >  derive it now
```

A gate that derives a document **writes it** to `docs/specs/<slug>/`, whichever command is
running. There is one artifact contract and two ways to fill it: supervised, one document at
a time with approval between them ({{cmd:deliver:spec}}), or unsupervised in a single pass
({{cmd:deliver:feature}}). The files that come out are the same files either way, which is
what makes a run resumable — edit `design.md` by hand and re-run, and your edit is the input.

### Everything for one feature lives in one folder

```
docs/specs/<slug>/
  requirements.md    gate 0
  design.md          gate 2
  tasks.md           gate 3
  report.md          gate 8
```

Committed, in a visible `docs/`, not a hidden dot-directory. Three reasons, all mechanical:
the spec diffs alongside the code that implements it; it sits inside the repo tree, which is
the only place the guidelines' `applies_to` globs and the `reviewer` subagent can see it; and
humans read it, which a dot-directory discourages.

If the repo has no `docs/`, create it. If the repo's own convention puts specs elsewhere,
follow the repo — and say so in the report.

### Staleness is checked, not assumed

Each derived document records the content hash of the one above it:

```yaml
---
spec: <slug>
gate: 2 Design
status: draft | approved
derived-from: requirements.md@a1b2c3d4e5f6
---
```

The hash is `git hash-object <path>`, first 12 characters — content, not commit, so it works
on files that were never committed.

**Before loading a document, recompute its upstream's hash.** On a mismatch the upstream was
edited after this document was derived, so this document is stale. Do not silently build
against it:

- {{cmd:deliver:spec}} — stop, name the two files, and ask whether to re-derive the
  downstream one or keep it and re-stamp.
- {{cmd:deliver:feature}} — re-derive the stale document and everything below it, and record
  in the report that it did and why.

`requirements.md` has no upstream, so it carries no `derived-from`.

---

## Gate 0 — Frame · *document*

Turn the requirement into **numbered acceptance criteria**, each one binary.

- `AC1`, `AC2`, … Each is a statement that is true or false when you look at the result.
- "Fast" is not a criterion. "P95 under 400 ms measured by the existing benchmark" is.
- Include the negative cases the requirement implies but does not say: what happens on empty
  input, on an upstream failure, on an unauthorised caller.
- List what you are **explicitly not** doing, where the requirement could reasonably be read
  more broadly.

Then run the coverage pass below. Then write `docs/specs/<slug>/requirements.md` from
[`templates/requirements.md.tmpl`](__SKILL_DIR__/templates/requirements.md.tmpl).

### The coverage pass

Before the criteria are final, dispatch **one fresh-context pass** whose only job is to find
what is missing. Give it the requirement and the criteria — **not** your reasoning, which is
the whole point: whoever wrote the criteria is the worst available judge of what they forgot.

It answers exactly these, and nothing else:

1. Which failure mode of this feature has no criterion?
2. Which non-functional requirement does this obviously imply and never state — latency,
   volume, retention, authorisation, cost, concurrency?
3. Which existing part of the system does this touch that no criterion mentions?
4. What does the *user's phrasing* assume is already true, that may not be?

Each finding lands in one of two places: a new criterion, or the **explicitly not doing**
list with a reason. Neither list may quietly drop it.

**Exit:** every criterion is numbered, binary, and traceable to something the user said or to
a stated assumption; the coverage pass has run and each of its findings is either a criterion
or a stated exclusion; `requirements.md` exists.

**Failure mode this prevents:** delivering something defensible that is not what was wanted,
and the narrower one the coverage pass targets — a complete-looking spec with a hole in it.
Unsupervised work drifts at gate 0 or not at all; by gate 4 the drift is already code.

**Ask the user only if** two readings of the requirement would produce materially different
systems. Otherwise assume, label the assumption `A1`, `A2`, and carry on.

---

## Gate 1 — Ground · *context, re-run every time*

Work out what kind of repo this is and load the standards that bind it.

1. Identify the type from the tree: an API, a pipeline, a job, an agent, a Genie space, a
   front end, or a mix.
2. Load the guidelines that apply — the language one, the resource one, and
   `service-structure` whenever there is service code.
3. Read enough of the existing code to match it. **The strongest standard is the surrounding
   code**: where a repo already has a convention, follow it and note the divergence from the
   written standard in the report rather than silently "fixing" it mid-feature.
4. Find the test command and the lint command. If you cannot find them, say so — do not
   invent one.

**Exit:** the repo type is named, and every guideline loaded is named, in whichever document
this run is about to write.

**Failure mode this prevents:** a technically correct change written in a dialect nobody else
in the repo uses.

---

## Gate 2 — Design · *document*

Follow the `design` guideline. Keep it proportionate — a one-file change gets five lines, a
new subsystem gets a page.

Required, whatever the size:

- Assumptions as `A1`, `A2`, … — only ones not already settled by the inputs.
- For each non-trivial decision: two options, the trade-off, and your recommendation.
- Risks with severity and mitigation.
- Which files you will add and which you will change.
- A row per acceptance criterion saying where in the design it is satisfied.

Write `docs/specs/<slug>/design.md` from
[`templates/design.md.tmpl`](__SKILL_DIR__/templates/design.md.tmpl), stamped with the
requirements hash.

**Exit:** every acceptance criterion from gate 0 maps to something in the design. A criterion
with no design is a criterion you are about to forget.

**Failure mode this prevents:** discovering the hard part at 80% done, and reshaping the
solution around the code already written.

---

## Gate 3 — Tasks · *document*

Break the design into tasks. This gate is deliberately narrow: it is not estimation, not
priority, not scheduling. For those, the requirement belongs in {{cmd:plan:release}}, which
owns the nine planning gates — running them for one feature is ceremony you do not need.

What makes a task well-formed (the same definition the plan skill's task-list gate uses, so
the two agree):

- **Complete, including the unglamorous work.** Migrations, config, fixtures, the test
  helper, the doc line. Work that is missing from the list is work that gets improvised at
  gate 4.
- **Named files.** Every task says which files it adds or changes. A task that cannot name
  its files is not decomposed yet.
- **No task bigger than one review.** If you would not want to read the diff in one sitting,
  split it.
- **Ordered by dependency**, with the dependency stated by task ID — not by intuition about
  what feels first.
- **Each task cites the criteria it serves**, by `AC` number.

Write `docs/specs/<slug>/tasks.md` from
[`templates/tasks.md.tmpl`](__SKILL_DIR__/templates/tasks.md.tmpl), stamped with the design
hash.

**Exit:** every `AC` from gate 0 appears against at least one task; every task names its
files and its criteria; every dependency resolves to a task ID in the same list.

**Failure mode this prevents:** the design that reads as complete and turns out to be four
tasks and one unexamined "and then wire it up". The AC-to-task mapping is mechanical on
purpose — it is checkable without judgement, which is what lets an unsupervised run check it.

---

## Gate 4 — Build

Create the branch first:

```
deliver/<slug>
```

Then implement, task by task in the order gate 3 set, against the standards from gate 1,
matching the surrounding code.

- **Zero TODOs in delivered code.** Implement it or state in the report that it is out of
  scope and why. A TODO in a report is information; a TODO in delivered code is a defect
  handed over silently.
- No commented-out code, no debug prints, no `console.log`.
- If a task turns out to be wrong or missing, **update `tasks.md`** rather than working
  around it in your head. The document is the plan of record.
- Run the linter and formatter before you finish this gate.

**Exit:** every task is done or explicitly dropped in `tasks.md` with a reason, every
criterion has code behind it, the linter passes, and the branch holds the work.

**Failure mode this prevents:** the 90%-done handoff, where the remaining 10% is the part
that was hard.

---

## Gate 5 — Review

Dispatch the **`reviewer` subagent**, in its own context. Give it:

- the diff (or the branch to diff against),
- the numbered acceptance criteria from gate 0,
- the names of the standards loaded at gate 1.

Then **record its verdict verbatim** — `PASS`, `PASS_WITH_CONDITIONS`, or `FAIL` — with its
critical issues and warnings, in the report.

**Exit:** a verdict exists and is in the report, whatever it says.

**Failure mode this prevents:** self-assessment. You have just spent a long context
convincing yourself this code is right; you are the worst available judge of it. This is why
the reviewer is a separate agent and not a checklist you walk yourself.

**Do not** argue with the review, soften it, or paraphrase it into something milder. If you
believe a finding is wrong, implement nothing, and record your disagreement as a note beneath
the verbatim finding.

---

## Gate 6 — Fix

Only on `FAIL`, or on `PASS_WITH_CONDITIONS` where a condition is cheap and clearly right.

```
round 1  fix every critical issue  →  re-run gate 5
round 2  fix what remains          →  re-run gate 5
round 3  fix what remains          →  re-run gate 5
round 4  DO NOT RUN — stop and report
```

- Fix **only** what the review raised. A fix round is not a refactor.
- If a round produces no change to the verdict, stop early — you are not converging.

**Exit:** verdict is `PASS` or `PASS_WITH_CONDITIONS`, **or** three rounds are spent.

**On exhaustion:** stop. Report the outstanding findings, the branch name, and what you tried.
This is a legitimate outcome and must be reported as `BLOCKED`, not dressed up as partial
success.

**Failure mode this prevents:** the unbounded loop — an agent alternating between two fixes,
burning budget, with nobody watching.

---

## Gate 7 — Test

Dispatch the **`qa` subagent** for test strategy and tests. Then **run them yourself**.

- Every acceptance criterion needs at least one test naming it.
- Every unhappy path the criteria imply needs a test.
- Where the change touches service code, include the structure tests from the qa guidance —
  layering, exception mapping, catch-all, log level, config validation.
- **Paste the actual test output** into the report. Not "tests pass" — the output.

**Exit:** the suite runs, and its real result is in the report.

**Failure mode this prevents:** two of them. Tests written but never executed, and a green
summary covering a red run.

**Never** weaken a test, loosen an assertion, mark a test skipped, or narrow a criterion to
reach green. A failing test in the report is a finding. A quietly deleted one is a lie.

---

## Gate 8 — Report

Fill in [`templates/report.md.tmpl`](__SKILL_DIR__/templates/report.md.tmpl) and write it to
`docs/specs/<slug>/report.md`, beside the three documents it closes out.

Then, in chat, five lines only:

```
Verdict     PASS | PASS_WITH_CONDITIONS | BLOCKED
Criteria    n of m met
Tests       n passed, n failed
Left        the single most important thing outstanding, or "nothing"
Assumed     the assumption that would most change the result if wrong
Report      <path>
```

**Exit:** the file exists and the path is in the chat summary.

**Failure mode this prevents:** the result living only in a conversation the user did not
watch. If the run is unsupervised, the artifact is the deliverable.
