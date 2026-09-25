# Review skill: why it is slow and inconsistent, and what to change

**Date** 2026-09-15 · **Status** implemented 2026-09-16, see `core/skills/review/` · **For** `core/skills/review/`, `core/subagents/reviewer.md`

---

## Brief

The skill is right about *what* to check and wrong about *how the work is shaped*. Four files
(848 lines) tell the model stories about past failures instead of giving it a procedure, every
mechanical step is done by the model in prose with a Bash round-trip each, the reviewer and the
consolidator speak different output formats, and two of the checks the user cares about most
(test coverage, comment quality) have no slot in the reviewer's output, so the consolidator has
nothing to merge and they vanish. Fixes, in order of payoff: one resolve script, one shared output
schema, a leaner template, prose cut to rules, and a fan-out threshold.

## 1. Diagnosis

| Symptom | Root cause | Where |
|---|---|---|
| Slow, "goes around" | Step 1 is 6–8 sequential git/glab calls, each preceded by ~20 lines of rationale the model re-reads every run. Glob matching, surface grouping, LLM-token grep, test-file diff and round detection are all done by the model, one Bash call at a time. | `SKILL.md` §1–2, `detection.md` |
| Slow | Instruction load before the diff is even read: orchestrator ~550 lines (`SKILL` 297 + `mr` 43 + `detection` 177 + 14 frontmatters); each reviewer ~500 (`reviewer.md` 331 + 2–4 conformance sheets). | all four files |
| Slow, wandering | `reviewer` has no `tools` restriction and inherits the heaviest model. Step 3 tells it to check sibling repos, so every reviewer may independently explore two or three other repositories. | `reviewer.md` frontmatter, `SKILL.md` §3 |
| Slow | Fan-out is the default: "one reviewer per surface" even for a 5-file MR. The collapse rule (<3 files) is weak and buried. | `detection.md` grouping |
| Inconsistent | Two formats. Reviewer emits Critical/Warning/Suggestion tables + gates + Positive + fix prompt; consolidator translates to P1/P2/P3 + a 12-row template. Translation is where things drift. | `reviewer.md` output, `SKILL.md` §5 |
| Inconsistent | Competing rules leave latitude: budget of 5 P1+P2 vs "report over budget and say why" vs "consolidation may not lower coverage severity". | `detection.md` rules 3, 9; `SKILL.md` §4 |
| Inconsistent | Duplicated and contradictory instructions: `mr.md` restates five of `SKILL.md`'s step-1 rules; `detection.md` rule 10 emits a Fix prompt the `SKILL.md` template has no row for; reviewer dimensions run 3, 3a, 3c, 3b. | `mr.md`, `detection.md`, `reviewer.md` |
| Skips tests | `reviewer` §6 defines coverage checks but the reviewer **output format has no Coverage section**. `SKILL.md` says "Coverage always present" — the consolidator writes it from memory or drops it. Same defect class as the Complexity row that was fixed on 2026-09-01. | `reviewer.md` output, `SKILL.md` §5 |
| Skips comments | Reviewer table has a Comment quality row, but merge rule 5 protects only Complexity ("never dropped"). Comment quality is dropped on merge. The mechanical scan (added comment blocks ≥5 lines → table) exists only in memory, not in the skill. | `detection.md` rule 5 |
| Verbose | Template has 12 rows before the first finding: Next, Scope, Round, 3–5-sentence Summary, two 6-row gate tables of mostly `pass`, Coverage, Parked, Not-done, Positive ×3, Verified ×3. A clean review is ~40 lines of scaffolding. Does not match the shape that landed on 2026-09-14 (fix table first, one block per finding, order at the end). | `SKILL.md` §5 |

## 2. Changes

Ordered by payoff over effort. 2.1 and 2.2 fix consistency and the skipped checks in an hour; 2.3
fixes time.

### 2.1 One output schema, shared by reviewer and consolidator

The reviewer emits exactly the block the final review uses: `P1/P2/P3 path:line defect → fix`,
a `Gates` line, a `Coverage` block, a `Comments` table. Consolidation becomes merge-and-cut, not
translate. Concretely:

- Add to `reviewer.md` output: **`### Coverage`** (the three items already in `SKILL.md` §5:
  tests the diff added / existing tests reaching changed modules / untested branches as
  `file:line`) and **`### Comments`** (`file:line | lines | cut to`). Mandatory, `none` allowed.
- Replace Critical/Warning/Suggestion tables with P1/P2/P3 lines. Delete the severity mapping
  from `detection.md` rule 6.
- `detection.md` rule 5: "Complexity **and Comment quality** rows are never dropped; the
  Coverage block is merged by union and its severity by max."
- Put the admissibility table in front of the reviewer too (or have it read `detection.md`), so
  a standalone reviewer has the same bar. Closes the open item in the gaps memory.

### 2.2 Template in the shape that landed

```
VERDICT  FAIL · Next: close 1–2, then mark ready
Scope    python, job · base dev · 14 files · round 2 (5 closed, 1 partly, 1 not done)

#  file:line              fix                                        size
1  src/task_02_x.py:88    MERGE on doc_id instead of blind append    M
2  resources/x.job.yml:31 catalog literal → var                      S

1  Problem … Fix …        (one block per P1/P2; code only where not obvious from prose)

P3       one-liners, no fix lines
Gates    service: all pass · databricks: env-values FAIL (#2), others pass
Coverage +0 tests · nothing existing imports task_02 · untested: task_02_x.py:91,104
Comments 2 blocks · task_02_x.py:12 (9 lines → 1), task_03_y.py:40 (7 → drop)
Parked / Not-done / Verified   one line each, only when non-empty
```

Cuts: Summary (the Next line is the summary), full pass-row gate tables, Positive as a section,
Round as its own row. Order is the fix table order, so the trailing "Order" list is gone too.

### 2.3 One resolve script replaces steps 1–2

`core/skills/review/scripts/resolve.sh <repo> <mr-id|branch>` writes to the scratch dir:

| File | Replaces |
|---|---|
| `meta.json` — state, draft, source, target, title, description, head sha | 1 glab call + parsing |
| `notes.md` — non-system notes; `previous_round.md` — last note starting `VERDICT:` | round detection by reading 100 notes |
| `diff.patch`, `files.txt`, `numstat.txt` — after the two fetches and the `FETCH_HEAD != origin/<target>` assertion, three-dot | 4 git calls and the two silent-failure modes the prose warns about |
| `surfaces.json` — glob match against guideline frontmatter + `detection.md` grouping + `python/validate.py` resolution | step 2 entirely |
| `llm_hits.txt` — the token grep over `.py`/`.sql` added lines | the `python-llm` decision |
| `tests.patch` — diff restricted to test paths; `touched_modules_imported_by_tests.txt` | the Coverage block's first two items |
| `comments.txt` — added comment blocks ≥5 lines, `file:line:count` | the Comments table |
| `complexity.txt` — `ruff check --select C90,PLR` over changed `.py` at `FETCH_HEAD` via `git show` into a temp dir | the Complexity row, deterministically |
| `per_surface/<name>.patch` | pasting scoped diffs into reviewer prompts |

It exits non-zero with one line on: fetch failure, merged/closed, empty diff, FETCH_HEAD equal to
the target. `SKILL.md` steps 1–2 shrink to "run it; read `meta.json` and `surfaces.json`; on
non-zero exit report the line and stop". Every rule that currently needs a paragraph of
justification becomes an assertion in the script. Check `STANDARD.md` for whether a skill may
ship a script; if not, the adapter installs it beside the skill.

### 2.4 Cut prose to rules

Move each "measured on a real repo…" / "on the review that prompted this rule…" paragraph to
`reference/rationale.md` (or the git log) and leave the rule as one line. Targets: `SKILL.md`
≤100 lines, `reviewer.md` ≤150, `mr.md` ≤15 (it only resolves the argument; delete its
restatement of step 1). Fix the dimension order (3, 3a, 3b, 3c). Decide the Fix prompt: either a
row in the template or delete `detection.md` rule 10.

### 2.5 Fan out only when it pays

Default is **one reviewer** holding all contracts. Fan out per surface only when the diff exceeds
~400 changed lines *and* spans more than one surface. Reviewer frontmatter gets
`tools: Bash, Read, Grep, Glob` (read-only) and an explicit "do not open sibling repositories".
The orchestrator does the sibling check once, only for findings that survived the bar. Consider
`model:` on the reviewer as a separate experiment; measure before deciding.

### 2.6 Settle the budget

One rule: at most five P1+P2 in the fix table; everything else that clears the bar is a P3
one-liner. Drop the "report over budget and say why" escape hatch. Coverage severity stays max
across reviewers, but a coverage P1 counts toward the five like any other.

## 3. Order of work

1. 2.1 + 2.2 — schema and template. Fixes the skipped Coverage/Comments and the format drift.
2. 2.3 — resolve script. Fixes time and the silent-failure prose.
3. 2.4 — trim. Half the token load per run, and the "going around" caused by narrative.
4. 2.5 + 2.6 — fan-out threshold and budget.
5. Re-run `install.sh`, review the same MR twice, compare the two outputs line by line. Two runs
   that agree on the fix table is the acceptance test.
