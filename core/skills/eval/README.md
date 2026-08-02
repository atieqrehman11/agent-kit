# eval

A Claude Code skill for giving a use case its **own evaluation** — a self-contained
`evaluation/` folder in the repo that owns it, wired to a generic eval engine that is
installed, never copied.

| Command | What it does | Direction |
|---|---|---|
| [`{{cmd:eval:new}}`](commands/new.md) | Scaffold `evaluation/` (spec + run wrapper + starter datasets) in the repo that owns the eval. | templates → repo |

## The split this skill enforces

- **The engine is generic.** One shared repo provides the `harness` package: adapters,
  judges, dataset loading, reporting, CLI. It contains nothing use-case-specific and is
  installed into the environment (`pip install -e <engine>`).
- **The spec is owned by the use case.** Each repo keeps its own `evaluation/spec.py` plus
  its CSVs. The spec declares *what* is under test (target, adapters, datasets, judges);
  the engine does the running.

Nothing is ever written back into the engine repo.

## What gets generated

```
<repo>/evaluation/
  spec.py          the one file you edit — target, datasets, judges
  run.sh           installs the engine if needed, then runs the eval
  README.md        run walkthrough + env overrides for this use case
  questions.csv    `smoke` set — quick screen (key,question,gold)
  benchmark.csv    `hard` set — graded benchmark (rubric columns)
  .gitignore       keeps eval-results/ out of git
```

## Targets

`{{cmd:eval:new}}` asks what the spec evaluates and wires the adapters accordingly — there is no
default, because it is the spec's core decision:

| Target | What it is |
|---|---|
| `agent-responses` | Deployed agent serving endpoint, `responses` schema (MAS / ChatAgent) |
| `agent-chat` | Deployed agent serving endpoint, chat / ChatCompletion schema |
| `http-backend` | REST backend answering `POST {"query": …}` → `{"answer": …}` |
| `openai` | OpenAI-compatible chat endpoint |

If a target speaks a contract none of these cover, pass your own request/response callables
inline in `spec.py`, or add a shared builder/parser to the engine's `adapters.py` and
reference it by name.

## How the engine is found

No path is hardcoded anywhere. The generated `run.sh` resolves the engine in this order:

1. `EVAL_ENGINE_PATH=/path/to/engine` — per-run / per-machine override,
2. the value baked in at scaffold time (`--engine-path`, else `$EVAL_ENGINE_PATH`, else the
   shared profile's `eval_engine_path`),
3. auto-detect — a sibling checkout of the repo that provides `harness/`.

Set `eval_engine_path` once in the shared profile sheet and apply it with
`{{cmd:scaffold:profile}}` to bake it into every eval you scaffold thereafter.

## Files

```
eval/
  new.md          new.py          scaffold-an-eval command + its script
  profile_fields.py               the profile field this skill owns (eval_engine_path)
  templates/                      every generated file, as a real file with TPLVAR_ tokens
    spec.py.tmpl  run.sh.tmpl  README.md.tmpl  questions.csv  benchmark.csv
```

---

See the top-level [README](../../../README.md) for install instructions.
