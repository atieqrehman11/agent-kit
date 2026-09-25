# Why the rules are what they are

Payload for `review`, read when a rule seems wrong. Each entry is the incident that produced a
rule, kept here so the rule itself can be one line.

**Fetch the two refs in separate commands; assert the head is not the target.** One
`git fetch origin <target> refs/merge-requests/<id>/head` leaves `FETCH_HEAD` on the *first*
ref. The diff became `target...target`, which is empty, and the empty-diff rule then reported
"nothing to review" on a 23-file merge request. `resolve.py` asserts it.

**The base is the fetched remote ref, never a local branch.** A local `main` four commits stale
reported three changed files for an already-merged MR. A stale checkout is the normal state of a
repo nobody is working in.

**Never mutate the repository.** A checkout of `FETCH_HEAD` followed by a "restore" to the
default branch moved the user off an in-progress feature branch in a sibling repo and made their
files appear to vanish. The git status in context describes the primary working directory, not
the repo being reviewed.

**An empty diff is a result.** Switching to a two-dot diff to manufacture content reviews
everything the target gained since the branch, under the merge request's name.

**Read the previous round.** A round-two review that had not read round one re-raised an item
round one had explicitly deferred, and reported as a defect a path name round one had itself
prescribed. Verifying the author's "addressed" reply was the highest-value work in that round:
`ruff` really was clean, the data really had moved to files, and "standardised the enum values
to uppercase" was only partly true.

**Settle what the change is for.** A review whose four blockers were all correct was unusable
because two of them applied to environments the author was not deploying to yet; the author had
to say "focus on dev" to get an answer out of it.

**Weight provisional code as provisional.** Three independent reviewers audited admittedly
fabricated mock figures for arithmetic agreement as though they were production numbers.

**Check the siblings before calling a convention a defect.** On one review the comparison
confirmed a blocker — two sibling bundles pinned a per-target host and variables, so deleting
both was a real divergence — and cleared a false one, because the hardcoded service-principal id
a reviewer flagged was byte-identical in both siblings. Neither call was available from the diff.

**Ask what the change exposes outside the team.** The two findings that mattered most on one
review came from no guideline: fabricated legal records naming real third-party companies in
seed data served to a browser, and a `TODO` admitting an endpoint was unauthenticated, which sat
in a docstring and was therefore published verbatim into `/openapi.json`.

**Cut before you order.** Three reviewers emitting full Critical/Warning/Suggestion sets produced
25 findings for an 1,100-line change when the useful answer was two, and the reader's reaction
was that it could not be trusted *because* it was long.

**Every gate table carries Complexity and Comments rows, and they survive consolidation.** Two
independent reviewers both walked the complexity dimension and neither wrote a word, because the
output had no row for it; the consolidator can only merge rows that exist. Coverage and comment
verbosity then went missing the same way — the reviewer's format had no slot for coverage, and
the merge rule protected only the Complexity row. The shared output schema exists so that a
check with no slot cannot happen again.

**The `Next` line is the answer.** `FAIL` describes the change, not what the author should do.

**One format, printed and posted.** A long version to read and a short version to post meant
the short one silently dropped findings and nobody could tell which was authoritative.

**Comment verbosity is a finding, not a footnote.** Asked for repeatedly; a review still shipped
with a one-line note about marker comments. `resolve.py` now lists every added block of five or
more lines so the reviewer starts from the list rather than from memory. The two recurring
shapes: a near-identical block at two call sites, and a multi-line trailing comment explaining
a rename.

**One reviewer by default.** Five reviewers over two files each cost more than they found, and
each one read the same 500 lines of contract before opening the diff.
