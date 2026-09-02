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
git fetch origin <target>                          # separate commands — see below
git fetch origin refs/merge-requests/<id>/head
git rev-parse FETCH_HEAD                           # must NOT equal origin/<target>
git diff origin/<target>...FETCH_HEAD
```

**Fetch the two refs in separate commands, and check `FETCH_HEAD` before diffing.** One
`git fetch origin <target> refs/merge-requests/<id>/head` writes both refs to `FETCH_HEAD` and
`FETCH_HEAD` then resolves to the **first** one — the target. The diff becomes `target...target`,
which is empty. Reproduced on a live 23-file merge request: the one-line form reported **0 changed
files**, the two-line form reported 23. This is the worst failure the skill has, because the rule
four paragraphs down says an empty diff is a result to report and stop on — so the two combine
into a confident "nothing to review" on a merge request that is full of changes. Assert
`git rev-parse FETCH_HEAD != git rev-parse origin/<target>` and stop if they match.

Measured on a real repo while this skill was being written: a local `main` four commits stale
reported **3 changed files for an already-merged merge request**. Against `origin/main` the same
MR correctly diffed to zero. A stale checkout is the normal state of any repo nobody is actively
working in, so this is the default failure, not an edge case. Fetching the MR without creating a
local branch also cannot collide with an existing branch.

**Never mutate the repository you are reviewing.** No `checkout`, no `stash`, no `reset`, no
branch creation — a review is a read. To read post-change content, use `git show FETCH_HEAD:<path>`
and `git grep <pattern> FETCH_HEAD -- <paths>`; both work without touching the working tree, and
subagents can be told to use them too. The reason is not tidiness: the git status in your context
describes the *primary* working directory, not the sibling repo the merge request lives in, so you
do not know which branch the user is on. Checking out `FETCH_HEAD` and "restoring" to the default
branch moved a user off an in-progress feature branch mid-session and made their files appear to
vanish. If a checkout is genuinely unavoidable, capture `git rev-parse --abbrev-ref HEAD` in that
repo first, restore to exactly that, and verify with `git status -sb` before reporting.

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

**Settle what the change is *for* before weighting anything.** A merge request targeting `dev`
that also edits the `stg` and `prod` blocks is a dev change that touches production config — the
production findings are real, but they are not what blocks it. Take the scope from the target
branch and the title, state it in the scope line, and put out-of-scope findings in a single
**Parked** line rather than mixing them into the blockers. Asked for on a review whose four
blockers were correct and where two of them applied to environments the author was not deploying
to yet: the author had to say "focus on dev" to get a usable answer out of a correct review.

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

**Check the change against its sibling repos before calling a convention a defect.** When the repo
is one of several built from the same template or deployed by the same controller, the siblings
are the only available statement of what the convention actually is. On the review that prompted
this rule the comparison did both jobs at once: it confirmed a blocker — two sibling bundles pinned
a per-target workspace host and per-target variables, so deleting both was a real divergence and
not the controller pattern the author believed — and it cleared a false one, because the hardcoded
service-principal id a reviewer had flagged was byte-identical in both siblings. Neither call was
available from the diff alone. Name the sibling and the file when a finding rests on it.

## 4. Consolidate

Rules, in `__SKILL_DIR__/reference/detection.md`. The five that change the outcome:

- **Worst verdict wins.** One `FAIL` makes the review `FAIL`.
- **Drop any standards finding that does not cite its rule and its line.** The reviewer is
  already required to; enforcing it here is what stops a plausible invention surviving.
- **Dedupe by file and line**, keeping the more specific statement.
- **Merge the structure gates** per shape, worst verdict per row — the service table and the
  Databricks table stay separate, because their rows are different checks. A review can emit
  one, the other, or both.
- **Every gate table carries a Complexity row**, from `reviewer` §3a, and it is never dropped.
  This is the check most often written and least often reported: §3a defines real limits — nesting
  depth, cyclomatic complexity, `and`/`or` in a function name, a boolean flag selecting behaviour,
  a class whose responsibility needs a conjunction — and on the review that prompted this rule,
  two independent reviewers both omitted it entirely, because the output shape had nowhere to put
  it. A reviewer that found nothing reports `pass`, exactly like the other rows. Silence is not
  `pass`; if no reviewer assessed it, the row is `n-a` and the scope line says so.
- **Coverage severity is the highest any surface reported, and consolidation may not lower it.**
  Take the max across reviewers and carry `reviewer` §6's severities through unchanged: a bug fix
  with no reproducing test, or an untested new error path in security-relevant code, stays
  CRITICAL. This is the rule most likely to be broken by the consolidator rather than the
  reviewer — a coverage gap reads as procedural next to a live security finding, and gets moved
  down the list precisely when the untested branch *is* the security finding.

## 5. Emit one review

Never post it. Print it, and offer to post — a comment on someone's merge request is
outward-facing and awkward to retract. Posting happens only when asked, and only with a forge
CLI that is authenticated.

**One review, one format.** What you print and what gets posted are the same text. Do not write a
long version to read and a short version to post: the short one silently drops findings, and
nobody can tell which version is authoritative. If it is too long, it is too long in both places —
cut by tightening findings, never by dropping them.

Output template. Every row of it, in this order:

```
VERDICT: PASS | PASS_WITH_CONDITIONS | FAIL

Scope     <guidelines applied> · base <target> (assumed, if it was) · <n> files, <n> surfaces
          · reviewed for <what the change is for>
Summary   3-5 sentences: what the change does, and what blocks it

Gates     merged table(s) — service, Databricks, or both, per what was touched.
          The Complexity row is part of every gate table and is never omitted.
Coverage  always present, including when the answer is none — see below

P1  <path:line>  <one sentence: the defect>  → <one sentence: the fix>
P2  <path:line>  ...
P3  <path:line>  ...

Parked    findings outside the stated scope, one line
Positive  what was done well, one line each
Verified  suspicions checked and refuted — so nobody re-raises them
```

Three rules make this readable, and all three were asked for after reviews that were correct and
still unusable:

- **Every finding opens with `path:line`.** `reference/detection.md` already uses `path:line` to
  *filter* subagent findings; that is a different job from putting it in front of the reader. A
  developer should be able to open the file from the finding without reading the sentence first.
- **Every finding carries P1 / P2 / P3**, defined once so it is not a judgement call: **P1** blocks
  the merge, **P2** must be fixed before the change reaches the next environment, **P3** is
  optional. Sort by priority, then by path. This replaces
  Critical/Warnings/Suggestions as *headings* — the reviewer subagent still reports in those
  buckets, and consolidation maps CRITICAL→P1, WARNING→P2, SUGGESTION→P3.
- **One line per finding, plus one line for the fix.** Evidence goes in only where a finding would
  otherwise be disbelieved — a reproduction, a quoted rule, a comparison against a sibling repo.
  A finding that needs a paragraph is usually two findings.

**Tone.** Address the change, not the author, and not yourself. State the defect, its consequence
and the fix; skip the editorialising, the scoring of your own thoroughness, and the adjectives.
"`deploy.sh` deploys to any target; `run_local.sh` refuses non-dev — make them agree" is the
register. This matters more than usual because the text is posted verbatim to a merge request
where the author's colleagues read it.

The scope line is not decoration. It is how someone reading the review later knows which standards
were applied, which were guessed at, and what the change was judged against.

**The test coverage row is never omitted**, including when the answer is "none" — that is the
result most worth stating, and a review that simply leaves it out reads as though coverage was
adequate. State three things:

- **What the diff added in tests** — resolved from the diff, not from the repo's overall coverage
  percentage. `git diff <base>...FETCH_HEAD -- 'tests/**' '**/test_*.py' 'conftest.py'`.
- **Whether any existing test reaches the changed modules**, when the diff added none. A repo with
  tests that import none of the changed files is at zero coverage for the change, which is a
  stronger statement than "no new tests" and needs to be made separately.
- **Which specific branches are untested**, named as file:line — the new `except` arms, both sides
  of a changed threshold, and any bug fix the diff's own comments describe. A list of branches is
  actionable; a coverage percentage is not.

## What this does not do

- **Approve, merge or post** without being asked.
- **Fix the code.** The fix prompt is the handoff; applying it is a separate deliberate step.
- **Re-review unchanged code.** A pre-existing violation in a file the diff merely touches is a
  warning naming the file, never a blocker.
