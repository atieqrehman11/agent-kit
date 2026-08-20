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
anthropic  openai  bedrock  langchain  langgraph  litellm  mlflow
ChatDatabricks  databricks_langchain  deploy_client
ai_query  ai_extract  ai_classify  ai_parse_document  ai_prep_search
ai_similarity  ai_gen  ai_summarize  ai_translate  ai_analyze_sentiment  ai_mask
ChatCompletion  invoke_model  messages.create  embeddings
vector_search  VectorSearchClient  similarity_search
serving_endpoint  foundation_model
```

**Grep `.sql` as well as `.py`.** A Databricks AI function is as often called from view or
UC-function DDL as from a stage file, and a retrieval surface reached only through SQL is still a
retrieval surface.

A hit anywhere in the added lines puts `python-llm` in scope for the surface that contains it.
Prefer a false positive here: the cost of loading it unnecessarily is a few hundred tokens, and
the cost of missing it is an unreviewed prompt-injection surface.

The list needs the retrieval half, not only the generation half. A vector-index stage that calls
no model directly still decides what reaches one later, and it trips none of the generation
names above.

**4. `python/validate.py` — the one path a glob cannot resolve.**

Both the agent and the genie repo type ship a validator at exactly this path, so no glob can put
the right guideline in scope for it. Resolve it from what else the repo holds, and add the
guideline as well as choosing the group:

| Repo also holds | Add | Group as |
|---|---|---|
| `src/managed/` | `agent` | Agent |
| `src/space.yml` | `genie` | Genie |

This matters most for the diff that touches *only* the validator. That file is the gating check —
CI's first stage runs it and the deploy script calls the same `check()` — so a change to it
changes what is allowed to deploy. Reviewed with only the `python` baseline in scope, a loosened
check reads as a tidy-up.

Record it in the scope line as added by detection, like `python-llm`.

## Grouping files into surfaces

One reviewer per group. A file belongs to exactly one group — the first that matches:

| Surface | Signal |
|---|---|
| Genie space | `src/space.yml`, `src/{data_sources,sql_functions,example_queries}.yml`, `src/instructions.md`, `src/{views,functions}/**`, `resources/genie*.yml`, `generated/space.*.json`, `python/build_space.py` |
| Agent | `src/managed/**`, `python/{deploy_agent,managed}.py`, and the `resources/deploy.job.yml` whose task runs the reconciler |
| Front end | `*.tsx`, `*.jsx`, `*.css`, front-end config |
| Pipeline | `pipeline/**`, `*.pipeline.yml` |
| Job | `*.job.yml`, the `src/task_NN_*.py` stage files a job resource names, and `src/ddl/**` |
| Service | `routers/**`, `services/**`, `repositories/**`, `schema/**`, `resources/*.app.yml` |
| Other Python | any remaining `.py` |
| Docs / config | everything else |

**The build and deploy scripts under `python/` belong to the surface they deploy, not to
"Other Python".** They are where the identity, drift and templating rules in the agent and
genie checklists are actually implemented — name-based resolution, declared-is-a-subset-of-live
tool comparison, `${catalog}` substitution — so a reviewer holding only the `python` baseline
cannot assess them. `python/validate.py` exists in both repo types and its name does not say
which: assign it by what else the repo holds — `src/managed/` makes it Agent, `src/space.yml`
makes it Genie. Resolve this before applying the first-match rule above, or the Genie row
claims an agent repo's validator.

**Prose is a reviewable surface.** `src/instructions.md`, `src/managed/instructions.md`, a tool
`description` and `example_queries.yml` are behaviour changes with no compile step and no test to
break. Route them to their own surface — never to Docs / config — because the eval and benchmark
gates that are the only check on them live in the agent and genie checklists.

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
4. **Merge the structure gates** by shape, worst verdict per row. The service gate and the
   Databricks gate are separate tables with different rows — never fold one into the other. A row
   no reviewer assessed is `n-a`, never blank; a table no reviewer emitted is omitted, not printed
   as four `n-a` rows.
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
