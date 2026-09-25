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

- **Empty** — run `python3 __SKILL_DIR__/resolve.py --list`, show the list, and ask which. Do not
  pick one, and do not review them all.
- **An id or a branch** — pass it to the script in step 1 of `{{cmd:review}}` and follow that
  skill in full. A branch with no open merge request is diffed against the default branch, and
  the scope line says there is no MR.

Print the review; do not post it.
