---
name: mr
kind: command
description: >
  Review a merge request against the standards its changed files trigger — one independent
  reviewer per surface, consolidated into a single verdict with a paste-ready comment. Give it
  an MR id, a branch name, or nothing to pick from the open list.
arguments: "[MR id, branch name, or blank to list open merge requests]"
---

# Review a merge request

`{{args}}` is an MR id, a branch name, or empty.

Follow `{{cmd:review}}` in full. This command only settles what is being reviewed:

- **An id** (`142`, `!142`) — that merge request.
- **A branch name** — the open merge request whose source is that branch. If none exists, diff the
  branch against the default branch and **say in the scope line that there is no MR**.
- **Empty** — list the open merge requests with their ids, titles and authors, and ask which. Do
  not pick one, and do not review them all.

Three things to get right before any reviewer is dispatched, because each silently invalidates the
result:

1. **The base is `origin/<target>`, fetched — never a local branch name.** A stale local `main` is
   the normal state of a repo and makes merged commits look like part of the change.
2. **The diff form is `git diff origin/<target>...FETCH_HEAD`**, three dots — and the target and
   the merge request head are fetched in **two separate commands**. Fetching both in one leaves
   `FETCH_HEAD` pointing at the target, which diffs to zero files on a merge request full of
   changes. Check `git rev-parse FETCH_HEAD` is not `origin/<target>` before you diff.
3. **The state.** A merged or closed merge request has nothing to review; report that and stop
   rather than diffing it.
4. **The repository is read-only.** No checkout, no stash, no reset — read post-change content
   with `git show FETCH_HEAD:<path>`. You do not know which branch the author is standing on.

Report the verdict, the scope line and the findings, in the single output format `{{cmd:review}}`
defines — the text you print is the text that would be posted, with no second shorter version.
Print it; do not post it.
