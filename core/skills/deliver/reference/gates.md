# The seven gates

One section per gate: what you do, the **binary** exit condition, the failure mode it exists
to prevent, and when to stop.

A gate's exit condition is checkable by someone who was not watching. "The design is good" is
not an exit condition. "Every acceptance criterion appears in the design" is.

---

## Gate 0 — Frame

Turn the requirement into **numbered acceptance criteria**, each one binary.

- `AC1`, `AC2`, … Each is a statement that is true or false when you look at the result.
- "Fast" is not a criterion. "P95 under 400 ms measured by the existing benchmark" is.
- Include the negative cases the requirement implies but does not say: what happens on empty
  input, on an upstream failure, on an unauthorised caller.
- List what you are **explicitly not** doing, where the requirement could reasonably be read
  more broadly.

**Exit:** every criterion is numbered, binary, and traceable to something the user said or to
a stated assumption.

**Failure mode this prevents:** delivering something defensible that is not what was wanted.
Unsupervised work drifts at gate 0 or not at all — by gate 3 the drift is already code.

**Ask the user only if** two readings of the requirement would produce materially different
systems. Otherwise assume, label the assumption `A1`, `A2`, and carry on.

---

## Gate 1 — Ground

Work out what kind of repo this is and load the standards that bind it.

1. Identify the type from the tree: an API, a pipeline, a job, an agent, a Genie space, a
   front end, or a mix.
2. Load the guidelines that apply — the language one, the resource one, and
   `service-structure` whenever there is service code.
3. Read enough of the existing code to match it. **The strongest standard is the surrounding
   code**: where a repo already has a convention, follow it and note the divergence from the
   written standard in the report rather than silently "fixing" it mid-feature.
4. Find the test command and the lint command. If you cannot find them, say so in the report —
   do not invent one.

**Exit:** the report's *Standards applied* section names each guideline loaded and the repo
type inferred.

**Failure mode this prevents:** a technically correct change written in a dialect nobody else
in the repo uses.

---

## Gate 2 — Design

Follow the `design` guideline. Keep it proportionate — a one-file change gets five lines, a
new subsystem gets a page.

Required, whatever the size:

- Assumptions as `A1`, `A2`, … — only ones not already settled by the inputs.
- For each non-trivial decision: two options, the trade-off, and your recommendation.
- Risks with severity and mitigation.
- Which files you will add and which you will change.

**Exit:** every acceptance criterion from gate 0 maps to something in the design. A criterion
with no design is a criterion you are about to forget.

**Failure mode this prevents:** discovering the hard part at 80% done, and reshaping the
solution around the code already written.

---

## Gate 3 — Build

Create the branch first:

```
deliver/<short-slug>
```

Then implement. Against the standards from gate 1, matching the surrounding code.

- Work criterion by criterion, in dependency order.
- **Zero TODOs in delivered code.** Implement it or state in the report that it is out of
  scope and why. A TODO in a report is information; a TODO in delivered code is a defect
  handed over silently.
- No commented-out code, no debug prints, no `console.log`.
- Run the linter and formatter before you finish this gate.

**Exit:** every criterion has code behind it, the linter passes, and the branch holds the
work.

**Failure mode this prevents:** the 90%-done handoff, where the remaining 10% is the part
that was hard.

---

## Gate 4 — Review

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

## Gate 5 — Fix

Only on `FAIL`, or on `PASS_WITH_CONDITIONS` where a condition is cheap and clearly right.

```
round 1  fix every critical issue  →  re-run gate 4
round 2  fix what remains          →  re-run gate 4
round 3  fix what remains          →  re-run gate 4
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

## Gate 6 — Test

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

## Gate 7 — Report

Fill in `templates/report.md.tmpl` and write it to `docs/delivery/<slug>.md` in the repo, or
alongside the branch if the repo has no `docs/`.

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
