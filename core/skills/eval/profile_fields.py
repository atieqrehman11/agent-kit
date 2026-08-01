"""Profile fields owned by the `eval` skill.

Picked up automatically by `{{cmd:scaffold:profile}}` (see `_sibling_fields` in
`scaffold/profile.py`) when both skills are installed, and read straight from the saved
profile by `new.py` when they are not. Same 6-tuple shape as the scaffold fields:

    (key, group, label, example, used_in, source)

Every field is optional — anything left blank stays a `TODO_SET_*` placeholder in the
generated `evaluation/` folder, or is resolved at run time from an environment variable.
"""

FIELDS = [
    (
        "eval_engine_path",
        "Evaluation",
        "Path to the shared eval engine checkout (the repo providing the `harness` package)",
        "$HOME/repos/eval-engine",
        "evaluation/run.sh (engine install path baked into the generated wrapper)",
        "wherever you cloned the eval engine (blank = auto-detect a sibling checkout,"
        " or set EVAL_ENGINE_PATH at run time)",
    ),
]
