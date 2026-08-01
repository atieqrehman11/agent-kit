# Scaffold an eval spec in the repo that owns it

Adds an `evaluation/` folder (`spec.py` + `run.sh` + `README.md` + starter `questions.csv`
and `benchmark.csv`) to the repo that will **own** its eval. Each use case owns its own
eval spec and data. The generated `run.sh` installs the engine if needed and runs the eval;
`README.md` documents it.

The shared eval engine is the generic **engine only** — it knows nothing use-case-specific
and is imported as the installed `harness` package, never copied. The generated spec
declares WHAT this use case evaluates (a deployed agent, an HTTP backend, …) and just names
the CSVs beside it — the engine builds each `Dataset`.

## Inputs

Collect these before generating. If `$ARGUMENTS` supplies the slug, use it; always confirm
the **repo** and **target** interactively.

| # | Name | Format | Resolution |
|---|---|---|---|
| 1 | **Repo** | path to the repo that owns the eval | asked (offer the repos found in the output dir) |
| 2 | **Slug** | kebab-case, matches the use case | asked (default: derived from the repo name) |
| 3 | **Target** | one of four keywords | asked — never assume a default |
| 4 | **Endpoint** | serving-endpoint name or `http(s)://` URL, or blank | asked (may be left for later) |

The **display name** is derived automatically (Title Case of the slug); the author can
rename it in the generated `spec.py` docstring later. The **engine path** is never asked —
it comes from `$EVAL_ENGINE_PATH`, else the shared profile's `eval_engine_path`, else the
generated `run.sh` auto-detects a sibling checkout that provides `harness/`.

## Steps

1. **Find the candidate repos** (no hardcoded paths — resolve them the same way
   `/scaffold:new` resolves where repos live):

```bash
ls -d "${SCAFFOLD_OUTPUT_DIR:-.}"/*/ 2>/dev/null
```

   If `$SCAFFOLD_OUTPUT_DIR` is unset, check the shared profile for `output_dir`
   (`python3 __SKILL_DIR__/../scaffold/profile.py --show`, if the scaffold skill is
   installed) and fall back to the current directory. Use the result as the option list in
   Tab 1 below; the user can always type any other path via "Other".

2. **Collect all inputs in ONE `AskUserQuestion` call — a wizard with one tab per
   question.** Do not ask sequentially or in plain text; issue a single `AskUserQuestion`
   containing these four questions (each becomes a tab). Every question offers the options
   below plus the automatic "Other" for free text.

   **Tab 1 — Repo** (`header: "Repo"`): the repo that will own this eval; an `evaluation/`
   folder is created under it. Offer the repos discovered in step 1 (up to four) as
   options; the user picks one or types another path via Other. Resolve the pick to an
   absolute path.

   **Tab 2 — Slug** (`header: "Slug"`): kebab-case, matches the use case. Pre-fill the
   first option with the slug derived from the chosen repo name (strip a leading `ai-`
   prefix and any `-backend` / `-api` / `-etl` / `-job` suffix); the user confirms or types
   another via Other. If `$ARGUMENTS` supplies a slug, pre-fill that.

   **Tab 3 — Target** (`header: "Target"`): the spec's core decision — do not assume a
   default. Four options (map the answer to the `<target>` keyword in parentheses):
   - **Deployed agent — responses** (`agent-responses`): a serving endpoint using the
     MAS / ChatAgent `responses` API. *Most deployed agents.*
   - **Deployed agent — chat** (`agent-chat`): a serving endpoint using the chat /
     ChatCompletion schema.
   - **HTTP backend** (`http-backend`): a REST service answering
     `POST {"query": ...}` → `{"answer": ...}`.
   - **OpenAI-compatible** (`openai`): a raw OpenAI-style chat endpoint.

   **Tab 4 — Endpoint** (`header: "Endpoint"`): serving-endpoint name for `agent-*`, or an
   `http(s)://` URL for `http-backend`/`openai`. To supply a value now, the user **types it
   into the "Other" free-text field** — that is the input box for this tab. Provide these
   options as shortcuts (all non-typed choices leave the endpoint blank so the script writes
   a `TODO`/local default):
   - **Set later (TODO)** — leave blank; fill the endpoint in after scaffolding.
   - **Use local default** — leave blank; the script's `http-backend`/`openai` local
     default is used.
   - *(Other)* — the automatic free-text option; type the serving-endpoint name or the full
     `http(s)://` URL here to set it now.

   Do not offer a "Provide now" option — it is a dead end, because a plain option cannot
   capture typed text. Only the "Other" field accepts a typed endpoint.

3. **Check for a collision** before writing. If `<repo>/evaluation/spec.py` already exists,
   flag it and confirm regenerating (`--force`) vs a different repo before running.

4. **Run the script** with the resolved values:

```bash
python3 __SKILL_DIR__/new.py \
  --slug "<slug>" \
  --target <agent-responses|agent-chat|http-backend|openai> \
  --repo "<repo-path>" \
  [--display-name "<name>"] \      # default: Title Case of the slug
  [--endpoint "<name-or-url>"] \   # omit to leave a TODO / local default
  [--engine-path "<path>"] \       # default: $EVAL_ENGINE_PATH, else profile, else auto-detect
  [--force]                        # regenerate over an existing spec
```

5. **Verify** the spec loads and imports cleanly. `run.sh` installs the engine if it isn't
   importable:

```bash
cd <repo>
./evaluation/run.sh --show     # prints target, adapters, datasets — no run
```

   If it reports the engine was not found, the install has no engine path configured: tell
   the user to re-run with `EVAL_ENGINE_PATH=/path/to/engine`, or to set `eval_engine_path`
   in the shared profile sheet and apply it with `/scaffold:profile`.

6. **Report** the created path and the next-steps the script printed: edit
   `evaluation/questions.csv`, fill `evaluation/benchmark.csv` (set
   `human_approval_status='approved'` on rows to include them), set the endpoint if left as
   TODO, then `./evaluation/run.sh smoke`. Point the author at the generated
   `evaluation/README.md` for the full run walkthrough.

## Notes

- The spec `name` is the slug with hyphens → underscores (e.g. `cable-health` →
  `cable_health`); the storage `use_case` slug stays hyphenated (`cable-health`).
- The generated `spec.py` names the CSVs (e.g. `"smoke": ("questions.csv", "…")`) and the
  engine builds each `Dataset`, deriving its exp/result/tag names from `(name, key)` and
  resolving the path beside `spec.py`. Run it with `./evaluation/run.sh <dataset>` (a thin
  per-repo wrapper that installs the engine if needed, then calls `ai-eval`); nothing is
  written into the engine repo. (Pass a pre-built `Dataset` only for a bespoke non-CSV
  loader.)
- Guidelines: `no_hallucination` is applied by the engine automatically (disable with
  `use_no_hallucination=False`). List other engine built-ins by NAME (e.g. `"cites_source"`)
  and add domain-specific `Guideline(...)` objects for anything case-specific.
- Judge cost: default `judge_mode="separate"` is one LLM call per judge. Set
  `judge_mode="panel"` to grade every criterion in ONE call per question (N calls, not
  N×judges) — each criterion still its own dashboard metric. Panel replaces the built-in
  Correctness/Relevance judges with the engine's combined prompt.
- `questions.csv` (smoke) is `key,question,gold` only → holistic judges. Add rubric columns
  to a row (or use `benchmark.csv`) to get element-level scoring + a failure report. See the
  engine's developer guide for the full CSV contract.
- Results land in `evaluation/eval-results/`: `<dataset>_report.md` (analysis page —
  question / expected / LLM answer / status / reason per failing question, answers
  truncated) + the full keyed `<dataset>_results.json`. `EVAL_SKIP_REPORT=1` skips the
  report; `EVAL_REPORT_ANSWERS=1` shows answers full-length.
- If the target speaks a request/response contract not already in the engine's
  `harness/agent/adapters.py`, either pass your own `(question)->payload` / `(raw)->answer`
  callables directly in the spec (no engine edit), or add a shared builder/parser to
  `adapters.py` and reference it by name.

## Example

```
/eval:new cable-health
→ [picker] Repo / Slug / Target / Endpoint?   ai-cable-health-api |
                                               cable-health |
                                               HTTP backend |
                                               (Other) http://localhost:8000/v1/chat/query
→ python3 __SKILL_DIR__/new.py --slug cable-health --target http-backend \
    --repo "<output-dir>/ai-cable-health-api" \
    --endpoint "http://localhost:8000/v1/chat/query"
✓ evaluation/ created → ./evaluation/run.sh --show
```
