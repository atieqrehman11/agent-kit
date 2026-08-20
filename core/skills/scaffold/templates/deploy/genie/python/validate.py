"""Check src/ without credentials or network — CI's first stage.

    PYTHONPATH=python python python/validate.py

run_local.sh runs this before every build, so "valid" has one definition. This
checks the DECLARATION only; whether a deploy would change the live space is a
separate question that needs the workspace, and `databricks bundle validate`
plus the deploy plan answer it.
"""

from __future__ import annotations

import glob
import os

import yaml

from build_space import load_space

CONFIG = "src/space.yml"
ROOT = "src"

# Files whose contents reach a workspace, and must therefore name
# ${catalog}.${schema} rather than a literal catalog — otherwise a stg deploy
# reads dev data.
TEMPLATED = (
    "example_queries.yml",
    "views/*.sql",
    "functions/*.sql",
)

# Deploy state the repo must not hold.
# Entry-level ids are NOT deploy state and are expected: they identify a piece of
# space CONTENT so an update edits it in place. It is the space's own id that must
# stay out of the repo — DAB owns that.
FORBIDDEN_KEYS = ("space_id", "genie_space_id")

# Referenced-file fields on space.yml. A tuple, not a bare string: iterating a
# string yields characters, and the check silently passes on all of them.
FILE_FIELDS = ("instructions_file", "example_queries_file")


def _declared_identifiers(space):
    """Every table and function identifier declared across src/."""
    tables = (space.get("data_sources") or {}).get("tables") or []
    return [
        t["identifier"] for t in tables if isinstance(t, dict) and t.get("identifier")
    ] + [
        f["identifier"]
        for f in (space.get("sql_functions") or [])
        if isinstance(f, dict) and f.get("identifier")
    ]


def _catalogs_from_bundle(path="databricks.yml"):
    """Every catalog any target deploys to, read from databricks.yml — the one
    place per-environment values live."""
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    default = ((doc.get("variables") or {}).get("catalog") or {}).get("default")
    out = {default} if default else set()
    for target in (doc.get("targets") or {}).values():
        catalog = (target.get("variables") or {}).get("catalog")
        if catalog:
            out.add(catalog)
    return {c for c in out if not str(c).startswith("TODO_SET_")}


def check(path=CONFIG):
    """Every problem with the declaration, so one run lists all of them."""
    problems = []
    if not os.path.exists(path):
        return [f"{path} does not exist"]

    root = os.path.dirname(path) or "."
    space = load_space(root)

    # Per-environment values live in databricks.yml — nothing to check here.

    tables = (space.get("data_sources") or {}).get("tables") or []
    if not tables:
        problems.append(
            "src/data_sources.yml: 'data_sources.tables' is empty — "
            "a space with no tables answers nothing"
        )
    for table in tables:
        if not isinstance(table, dict) or not table.get("identifier"):
            problems.append(
                f"src/data_sources.yml: every tables entry needs an 'identifier' — got "
                f"{table!r}. A bare string is the old shape and would strip column_configs."
            )

    for key in FORBIDDEN_KEYS:
        if key in space:
            problems.append(
                f"{path}: remove {key!r}. Deploy state does not belong in the repo — "
                "DAB owns the space id"
            )

    for field in FILE_FIELDS:
        ref = space.get(field)
        if ref and not os.path.exists(os.path.join(root, ref)):
            problems.append(f"{path}: {field} {ref!r} does not resolve to a file")

    for function in space.get("sql_functions") or []:
        if not isinstance(function, dict) or not function.get("identifier"):
            problems.append("src/sql_functions.yml: every entry needs an 'identifier'")
            continue
        ddl = function.get("ddl")
        if ddl and not os.path.exists(os.path.join(root, ddl)):
            problems.append(
                f"src/sql_functions.yml: ddl {ddl!r} does not resolve to a file"
            )

    # A literal catalog in a deployed file is the regression this guards: it
    # survives substitution untouched, so a stg deploy would silently read dev.
    for identifier in _declared_identifiers(space):
        if not identifier.startswith("${catalog}.${schema}."):
            problems.append(
                f"{identifier!r} does not start with '${{catalog}}.${{schema}}.' — "
                "a literal catalog makes a stg/prod deploy read the wrong data"
            )

    known_catalogs = _catalogs_from_bundle()
    for pattern in TEMPLATED:
        for f in sorted(glob.glob(os.path.join(root, *pattern.split("/")))):
            with open(f, encoding="utf-8") as handle:
                body = handle.read()
            for catalog in known_catalogs:
                # Skip comment lines: they may cite a concrete catalog when
                # recording a verification result, which changes nothing at deploy.
                hits = [
                    n
                    for n, line in enumerate(body.splitlines(), 1)
                    if catalog in line and not line.lstrip().startswith(("#", "--"))
                ]
                if hits:
                    problems.append(
                        f"{f}: literal catalog {catalog!r} on line(s) "
                        f"{', '.join(map(str, hits))} — use ${{catalog}}.${{schema}}."
                    )

    if "sample_questions" in space:
        problems.append(
            f"{path}: remove 'sample_questions' — the serialized_space v2 schema has "
            "no field for them, so they cannot be deployed"
        )

    return problems


def main():
    problems = check()
    if problems:
        for p in problems:
            print(f"ERROR: {p}")
        return 1
    print(f"✓ {ROOT}/ valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
