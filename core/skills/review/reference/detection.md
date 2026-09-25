# Detection, admissibility and consolidation

Payload for `review`. `resolve.py` implements §1 and §2 — they are written here so the rules
have one prose home and so a review without the script can apply them by hand. §3 and §4 are
the consolidator's rules, and the reviewer applies §3 to its own output before it emits.

## 1. What the globs miss

The guidelines' `applies_to` globs are the mapping; nothing keeps a repo-to-standard table. Four
additions the globs cannot express:

| Signal | Adds | Why |
|---|---|---|
| any `.py` / any `.java` | `python` / `java` | language baselines carry no useful glob |
| a model or retrieval call in an **added** `.py` or `.sql` line (`LLM_TOKENS` in `resolve.py`: `ai_query`, `anthropic`, `openai`, `vector_search`, `embeddings`, …) | `python-llm` | a retrieval stage that calls no model still decides what reaches one; a false positive costs a few hundred tokens, a miss is an unreviewed prompt-injection surface |
| `python/*.py` in a repo holding `src/managed/` → agent; holding `src/space.yml` → genie | that guideline, and that surface | `python/validate.py` is CI's gating check in both repo types, and its name does not say which |
| a service group exists | `service-structure` | it is the contract for the service structure gate |

Docs-and-config-only files are reviewed against the repo-type guideline (`agent`, `genie`, or
`api` for a service) — deploy-time breakage lives in `databricks.yml` and CI config.

## 2. Surfaces

First match wins:

| Surface | Signal |
|---|---|
| genie | `src/space.yml`, `src/{data_sources,sql_functions,example_queries}.yml`, `src/instructions.md`, `src/{views,functions}/**`, `resources/genie*.yml`, `generated/space.*.json`, `python/build_space.py` |
| agent | `src/managed/**`, `python/{deploy_agent,managed}.py`, a `resources/*.job.yml` that runs the reconciler |
| frontend | `*.tsx`, `*.jsx`, `*.css`, front-end config |
| pipeline | `pipeline/**`, `*.pipeline.yml` |
| job | `*.job.yml`, `src/task_NN_*.py`, `src/ddl/**` |
| service | `routers/**`, `services/**`, `repositories/**`, `schema/**`, `resources/*.app.yml` |
| python | any remaining `.py` — folds into the largest code surface when one exists |
| docs-config | everything else |

- **Tests are not a surface.** Every reviewer receives `tests.patch`; coverage is judged per
  surface against it.
- A surface under three files folds into the largest one.
- **Fan-out** only when the diff exceeds 400 changed lines *and* more than one surface remains.
  Otherwise one reviewer holds every contract.
- **Prose is a surface.** `instructions.md`, a tool `description`, `example_queries.yml` are
  behaviour changes with no compile step; the agent and genie rows catch them, and the eval and
  benchmark gates in those sheets are their only check.

## 3. What is not a finding

Applied before anything is ordered. Each row was reported at least once on a review whose reader
then judged the whole document padded.

| Not a finding | Why |
|---|---|
| A convention the sibling repo also follows | the siblings are the statement of the convention |
| A style rule the same file already breaks elsewhere | a sweep, not a review finding |
| Pre-existing, in a file the diff merely touches | one P3 naming the file, never ranked higher |
| Service-wide and not introduced here | an architecture ticket, not this author's defect |
| A latent hazard with no reachable failure | one clause under Verified, or nothing |
| Longer to explain than to fix | a comment, not a finding |
| A restatement of another finding's cause | fold it into that finding's fix line |

The bar never drops a finding for being awkward. Density above about one finding per hundred
changed lines means the bar was not applied, not that the change is unusually bad.

## 4. Consolidation

1. **Merge by `path:line`.** Keep the more specific statement and the higher priority.
2. **Discard a standards finding that does not quote its rule and name its line.** Dropped, not
   downgraded — the reviewer was required to, so one without them is an invention.
3. **Apply §3**, and record the count for the `Dropped` row.
4. **Derive the verdict.** Any P1 → `FAIL`; P2 and no P1 → `PASS_WITH_CONDITIONS`; else `PASS`.
5. **Budget.** At most five P1+P2 in the fix table. Beyond that, the weakest become P3
   one-liners — a coverage P1 counts like any other and is never lowered to make room.
6. **Gates.** One `Gates` line naming each table a reviewer emitted; only non-pass rows are spelled
   out. The Complexity and Comments rows are never dropped; a row no reviewer assessed is `n-a`
   and the scope line says so. Service and Databricks tables are never folded into each other.
7. **Coverage.** Union of the three items across reviewers; severity is the maximum reported.
8. **Comments.** Union of the reviewers' tables.
9. **Every finding opens with `path:line`**, one line in the table; a Problem/Fix block for P1
   and P2 only, with code only where the fix is not obvious from prose.
10. **Order** by priority, then by path. Within P1: security, correctness, structure.

## 5. The scope line

```
Scope  api, service-structure, python, python-llm (detected) · base main (assumed) · 14 files, +310/−42
       · 2 surfaces · reviewed for the dev deploy · round 2: 5 closed, 1 partly, 1 not done
```

`(assumed)` whenever the target was not read from the forge API; `(detected)` on every guideline
added by §1 rather than a glob. Someone reading the review a month later needs to know what was
checked and what was guessed.
