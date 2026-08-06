# Surface detection and consolidation

Payload for `review`. Read after matching the guidelines' `applies_to` globs against the changed
files — this covers what the globs cannot express, and how several reviewers become one verdict.

---

## What the globs miss

Three additions. Nothing else is hardcoded: the globs remain the mapping.

**1. Language baselines have no useful glob of their own.**

| Changed files include | Add |
|---|---|
| any `.py` | `python` |
| any `.java` | `java` |
| any `.tsx` / `.jsx` | already matched by `react` |

`python-llm` deliberately carries no `**/*.py` glob — it would fire on every Python file
alongside `python`. So it is added by detection, below.

**2. `service-structure` whenever service code is touched.**

Its own globs cover `routers/`, `services/`, `repositories/`, `controller/`, `service/`,
`repository/`, so this mostly falls out of step 2. State it explicitly anyway: it is the contract
for the reviewer's structure gate, and that gate is not optional.

**3. `python-llm` when the diff contains a model call.**

Detected from the diff content, never from the repository name. Grep the added lines for any of:

```
anthropic  openai  bedrock  langchain  langgraph  litellm
ai_query  ai_extract  ai_classify  ai_parse_document  ai_prep_search
ChatCompletion  invoke_model  messages.create  embeddings
serving_endpoint  foundation_model
```

A hit anywhere in the added lines puts `python-llm` in scope for the surface that contains it.
Prefer a false positive here: the cost of loading it unnecessarily is a few hundred tokens, and
the cost of missing it is an unreviewed prompt-injection surface.

## Grouping files into surfaces

One reviewer per group. A file belongs to exactly one group — the first that matches:

| Surface | Signal |
|---|---|
| Genie space | `genie-space/**` |
| Agent | `supervisor/**` |
| Front end | `*.tsx`, `*.jsx`, `*.css`, front-end config |
| Pipeline | `pipeline/**`, `*.pipeline.yml` |
| Job | `*.job.yml`, and the `src/main.py` a job resource names |
| Service | `routers/**`, `services/**`, `repositories/**`, `schema/**`, `app.yml` |
| Other Python | any remaining `.py` |
| Docs / config | everything else |

**Docs-and-config-only changes get one reviewer, not none** — a changed `databricks.yml`,
`.gitlab-ci.yml` or per-environment config is where deploy-time breakage lives. Review it against
the repo-type guideline alone.

Collapse a group with fewer than ~3 changed files into the nearest related group. Five reviewers
over two files each costs more than it finds.

## Consolidation

In order:

1. **Verdict** — worst wins. Any `FAIL` → `FAIL`. Any `PASS_WITH_CONDITIONS` and no `FAIL` →
   `PASS_WITH_CONDITIONS`.
2. **Discard unsupported standards findings.** A standards finding must quote the rule it breaks
   and name the file and line. One that does neither is dropped, not downgraded — the reviewer's
   own instructions require it, so a finding without them is an invention.
3. **Dedupe by file and line.** Keep the more specific statement; if two reviewers disagree on
   severity, keep the higher and note both surfaces.
4. **Merge the structure gates** into one four-row table, worst verdict per row. A row no reviewer
   assessed is `n-a`, never blank.
5. **Order by severity, then by file.** Critical first. Within critical, security before
   correctness before structure.
6. **Fix prompt** — one block, concatenating every critical issue across surfaces, deduped.

## The scope line

```
Scope  api, service-structure, python, python-llm · base main (assumed) · 14 files, 2 surfaces
```

Mark **`(assumed)`** on the base whenever the target branch was not read from the forge API, and
name any guideline that was added by detection rather than by a glob match. Someone reading the
review a month later needs to know what was actually checked and what was guessed.
