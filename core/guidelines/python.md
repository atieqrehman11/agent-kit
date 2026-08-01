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

## Error handling

Catch, log with context, and **re-raise** — never silently swallow.

```python
try:
    df = spark.read.format("delta").load(table_path)
except Exception as e:
    print(f"Error loading table {table_path}: {e}")
    raise
```

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

## Code reuse

- Extract shared logic into `src/utils/`.
- No duplication across notebooks; prefer configuration-driven design.

---

## Databricks compute (notebook / job / pipeline / agent code)

- Access the pre-initialized `spark` session; use `dbutils` for widgets, secrets, filesystem.
- Prefer the DataFrame API over RDDs, and PySpark functions over UDFs; rely on lazy evaluation.
- **Logging:** `print()` is acceptable for driver logs in notebooks/jobs (surfaced in run
  logs) — include context (env, catalog, counts, progress). **API code uses the `logging`
  module / structured logs** per the API guidelines, not `print`.
- **Unity Catalog access:** use the three-level namespace `catalog.schema.table`; rely on
  managed identities for access; use `spark.sql()` for DDL; query `information_schema` for
  metadata. (Table **naming** conventions live in `PIPELINE_STANDARDS.md`.)
