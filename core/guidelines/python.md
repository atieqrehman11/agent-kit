---
name: python
kind: guideline
description: >
  Baseline standards for all Python in any repo type: style, import organisation, function
  design, error handling, configuration, testing, code reuse, and Databricks compute
  conventions. Applies whenever Python is written or reviewed.
applies_to:
  - "**/*.py"
---

# Python Standards — __ORG_PREFIX__shared standard, all repo types

Cross-cutting **code** standard for every repo. This is the *how to write
Python here* layer; pair it with your repo's **resource** standard
(`API_STANDARDS.md` / `PIPELINE_STANDARDS.md` / `JOB_STANDARDS.md` / `AGENT_STANDARDS.md` /
`GENIE_STANDARDS.md`), which covers *how to build this resource type*. The two layers do not
overlap — style and structure live here, domain patterns live there.

> **Service code also follows [`service-structure`](./service-structure.md)** — the layer
> chain, where models live, one exception hierarchy behind one boundary handler, log levels
> from configuration, and no hardcoded prompts or thresholds. This document does not repeat
> those rules. Where the two appear to conflict, see the note under *Error handling*.

> Adopted from the enterprise Python rules so every coding assistant applies the **same**
> rules. Keep this in sync with the enterprise copy rather than forking it.

## Applies to

All Python in the repo. The **Databricks compute** section (logging, Unity Catalog) applies
to notebook / job / pipeline / agent code that runs on Databricks compute. An `api` repo
follows the logging and error rules through its framework and the API guidelines — not the
notebook idioms.

---

## Style

- Follow **PEP 8**. Target **Python 3.12+**.
- **Type hints** on every function signature.
- **Docstrings** on public functions and classes (parameters + return).
- **Max line length: 100.**
- Use **Ruff** for both linting and formatting (Ruff's formatter is Black-compatible). Config
  ships in `pyproject.toml` (`line-length = 100`, `target-version = "py312"`). Run
  `ruff check` and `ruff format` before every commit.

## Import organization

Group and separate with blank lines: standard library, third-party, then local.

```python
# Standard library
import os
from datetime import datetime

# Third-party
import yaml
from pyspark.sql import functions as F

# Local
from utils import helper_functions
```

## Function design

- Small and single-responsibility; descriptive names.
- Type hints and a docstring on each.
- **Return early** for error conditions rather than nesting.

## Complexity limits

Numbers, not adjectives, so Ruff fails the build and nobody has to win an argument about what
"small" means.

| Metric | Limit | Ruff rule |
|---|---|---|
| Cyclomatic complexity per function | **10** | `C901` |
| Branches per function | **12** | `PLR0912` |
| Statements per function | **50** | `PLR0915` |
| Nested blocks (`if`/`for`/`while`/`with`/`try`) | **4** | `PLR1702` (preview) |
| Parameters per function | **5** | `PLR0913` |

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "C90", "SIM", "PLR0912", "PLR0913", "PLR0915"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-args = 5
max-branches = 12
max-statements = 50

# Notebook and pipeline code: spark/dbutils are injected, and cells legitimately
# put imports and statements where a module would not.
[tool.ruff.lint.per-file-ignores]
"**/pipeline/**" = ["F821", "E402", "E501", "E702"]
"**/notebooks/**" = ["F821", "E402", "E501", "E702"]
```

Two details that config gets right, both measured on real repos here: **name the complexity
rules** rather than selecting `PL` wholesale — blanket `PL` turned 3 real findings into 31, the
3 still there but buried — and **exempt notebook and pipeline paths**, where 123 violations were
`F821` on injected `spark`/`dbutils` plus cell idiom, and *none* were complexity.

**Nesting depth is the one to hunt.** Each level multiplies the paths a test must cover, and the
innermost branch is the one nobody exercises. In order: guard clause and early return; combine
with `and` (`SIM102`); extract the inner block into a named function; replace an `if/elif` chain
over a value with a dict or `match`.

**Return count is deliberately not capped** — `PLR0911` would penalise those guard clauses.

A `# noqa: C901` needs a comment saying why the function is irreducible. A bare `noqa` is a
failed review, not a passed lint.

## Single responsibility

"One reason to change", with a mechanical tell at each level so this is checkable rather than
aesthetic:

- **Function** — nameable without `and` or `or`. A flag parameter that selects between two
  behaviours is two functions.
- **Class** — one sentence, no conjunction. Methods that split into two groups sharing no
  attribute are two classes.
- **Module** — one public concept per file. Single-use helpers are private to their caller;
  helpers three modules use belong in `src/utils/`.

Size is a symptom rather than the rule, and these are review checks, not lint failures: a
function past **50 lines**, a class past **200**, or a module past **400** usually has a seam —
look for it before accepting the size.

Where a responsibility is allowed to *live* is [`service-structure`](./service-structure.md).

## Error handling

Catch, log with context, and **re-raise** — never silently swallow.

```python
try:
    df = spark.read.format("delta").load(table_path)
except Exception as e:
    print(f"Error loading table {table_path}: {e}")
    raise
```

**In a service, this rule narrows.** Catch a *specific* exception, add context, and re-raise
as a **domain exception**; a bare `except Exception` is allowed only in the single catch-all
handler at the boundary. Which exception maps to which response code, and who is allowed to
build an error body, is [`service-structure`](./service-structure.md) §3 — not this file.

## Configuration handling

Configuration-driven by default. Load and **validate** YAML; fail loudly on a missing key.

```python
def load_config(config_path: str) -> dict:
    """Load and validate a YAML config."""
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    assert "environments" in config, "Missing 'environments' in config"
    assert "tasks" in config, "Missing 'tasks' in config"
    return config
```

## Testing

- Tests in `tests/`, using **pytest**.
- Mock `dbutils` / `spark` for local runs.
- Cover config loading/validation and transformation logic.
- Name tests `test_given_<state>_when_<action>_then_<outcome>` — the name states the case, so a
  failure report is readable without opening the file.

### New logic ships with its tests

**Every branch this change adds is tested by this change** — the diff, not the module. Repo
coverage percentage is not the gate; it is satisfiable by testing the easy modules.

**Needs a test:** each arm of a new conditional, loop or `except` in business logic, not just the
arm the happy path takes; every new function that is not a pure pass-through; every changed
threshold, operator or default, on both sides; every domain exception the code can raise. **A bug
fix ships a test that fails without the fix** — otherwise the fix has no evidence.

**Does not:** renames, type hints, formatting, docstrings, config values carrying no logic.

Named edge cases: empty input, empty collection, zero results, `None` where the type allows it.
Mock at the I/O seam — the repository or client class, per
[`service-structure`](./service-structure.md) — not inside the logic under test. A test that only
asserts nothing raised is not a test; assert the value.

## Code reuse

- Extract shared logic into `src/utils/`.
- No duplication across notebooks; prefer configuration-driven design.

---

## Databricks compute (notebook / job / pipeline / agent code)

- Access the pre-initialized `spark` session; use `dbutils` for widgets, secrets, filesystem.
- Prefer the DataFrame API over RDDs, and PySpark functions over UDFs; rely on lazy evaluation.
- **Logging:** `print()` is acceptable for driver logs in notebooks/jobs (surfaced in run
  logs) — include context (env, catalog, counts, progress). **This allowance does not extend
  to service code**, which uses the `logging` module with the level read from configuration —
  see [`service-structure`](./service-structure.md) §4.
- **Unity Catalog access:** use the three-level namespace `catalog.schema.table`; rely on
  managed identities for access; use `spark.sql()` for DDL; query `information_schema` for
  metadata. (Table **naming** conventions live in `PIPELINE_STANDARDS.md`.)

---

## Conformance

The audit checklist for this guideline lives beside it, in [`conformance/python.md`](conformance/python.md) — one file, one source of truth, loaded by whoever is auditing rather than by everyone who edits a file.
