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
  bin: [glab, ruff]
---

# Review

Four steps. Step 1 is a script and step 2 reads its output; judgement starts at step 3. Why each
rule exists is in `__SKILL_DIR__/reference/rationale.md` — read it when a rule seems wrong, not
before every review.

## 1. Resolve — run the script; do not redo its work by hand

```
python3 __SKILL_DIR__/resolve.py --repo <repo> --out <scratch>/review <id | branch>
```

It fetches both refs, asserts the head is not the target, diffs three-dot against the merge base,
reads the MR state, description and discussion notes, matches the changed files against the
guidelines' own `applies_to` globs, groups them into surfaces, and pre-computes the checks a
reviewer forgets: test files in the diff, existing tests reaching each changed module, added
comment blocks, ruff complexity at the head, model-call detection. Read `<out>/summary.md` — one
screen — and open the other files only as needed.

Exit codes are results, not errors to work around:

| Exit | Meaning | Do |
|---|---|---|
| 3 | merged or closed | report it and stop |
| 4 | fetch failed, or the head equals the target | print the script's last line and stop — never fall back to the working tree |
| 5 | empty diff | report it and stop — never switch to a two-dot diff |

**The repository is read-only.** No checkout, stash, reset or branch. Post-change content is
`git show <head>:<path>`; searching it is `git grep <pattern> <head> -- <paths>`.

## 2. Settle what the script cannot

Three judgements, each one clause in the scope line:

- **What the change is for.** Take it from the target branch and the title. A change to `dev`
  that also edits `stg`/`prod` blocks is a dev change; findings outside that go on one **Parked**
  line, never among the blockers.
- **What is provisional.** Code behind a flag only one environment sets, or whose own comments
  name its deletion path, earns blockers only for what survives its deletion: the contract
  shape, the gate, and anything exposed outside the team.
- **The round.** `summary.md` says which round this is. If `previous_round.md` exists, read it.
  Three rules bind: an item the previous round deferred is not a blocker now; a design the
  previous round prescribed is not a defect now — if you disagree, say it was prescribed; the
  author's "addressed" replies are claims, and each resolves to **closed / partly / not done**.

## 3. Dispatch

`summary.md` says `Fan-out: yes` or `no`. **No** is the default: one `reviewer` subagent holding
every listed contract. **Yes** — over 400 changed lines across more than one surface — means one
reviewer per listed surface, in parallel. Give each reviewer paths, not pasted text:

- its `per_surface/<name>.patch` (or `diff.patch`), the head sha, the merge base, the repo path
- the explicit guideline list from `summary.md` for its surface — it infers nothing
- `tests.patch`, `tests_reaching.txt`, `comments.txt`, `complexity.txt`, `llm_hits.txt`
- the MR title and description; `previous_round.md` when it exists
- the instruction that the repo is read-only and that it must not open sibling repositories

Two checks are yours, done once, on the findings that come back:

- **Siblings.** Before a convention finding stands, compare the sibling repos built from the same
  template. Byte-identical in a sibling → drop it as the convention; divergent → it stands and
  names the sibling file. Only for survivors; reviewers do not roam.
- **Exposure.** Of every surface that serves data, renders a page or publishes a schema, ask
  what it exposes outside the team: seed data naming real companies, a docstring `TODO`
  published into `/openapi.json`. No guideline asks this.

## 4. Consolidate and emit

Reviewers report in the final format, so this is merge-and-cut, never translation. Rules in
`__SKILL_DIR__/reference/detection.md` §4; the ones that decide the outcome:

- The verdict is derived: any P1 → `FAIL`; P2 only → `PASS_WITH_CONDITIONS`; else `PASS`.
- Apply the admissibility bar (§3) and say how many findings it dropped.
- Budget: at most five P1+P2 in the fix table; the weakest beyond that become P3 one-liners.
- Coverage and Comments merge by union and are never dropped; the Complexity and Comments gate
  rows are never dropped.

Template — every row, this order. What you print is what gets posted; there is no second version:

```
VERDICT   FAIL · Next: <the one action the author takes now>
Scope     <guidelines; "(detected)" where added by detection> · base <target>[ (assumed)] · <n> files, +a/−d
          · <n> surface(s) · reviewed for <purpose>[ · provisional: <surface>][ · round n: x closed, y partly, z not done]

#  P   file:line                 fix                                          size
1  P1  src/task_02_x.py:88       MERGE on doc_id instead of blind append      M
2  P2  resources/x.job.yml:31    catalog literal → bundle variable            S

1  Problem  <path:line — the defect and its consequence, one or two sentences>
   Fix      <one sentence; code only where the change is not obvious from prose>

P3        file:line — change · file:line — change
Gates     service: all pass | databricks: env-values fail (#2), others pass · complexity pass · comments fail
Coverage  +<n> tests in diff · <n> of <m> changed modules reached by no test · untested: path:line, path:line
Comments  path:line (<n> lines → <cut to>) · path:line (<n> → drop) | none
Parked    <out-of-scope findings — only when non-empty>
Not-done  <what was out of reach — only when non-empty>
Verified  <suspicions checked and cleared, so nobody re-raises them — one line>
Dropped   <n> findings as inadmissible
```

P1 blocks the merge; P2 is fixed before the change reaches the next environment; P3 is optional.
A Draft MR's `Next` says what to close before it is marked ready. **Tone:** address the change,
not the author — the defect, its consequence, the fix; no adjectives, no scoring of your own
thoroughness.

**Never post.** Print it and offer to; posting needs the user to ask and an authenticated CLI.

## What this does not do

- Approve, merge or post unasked. Fix the code — the review is the handoff.
- Re-review unchanged code: a pre-existing violation in a touched file is a P3 naming the file.
