"""Check genie-space/space.yml. No credentials, no network — CI's first stage.

    python src/validate.py

deploy.py calls check() too, so "valid" has one definition.
"""

from __future__ import annotations

import os
import sys

import yaml

CONFIG = "genie-space/space.yml"

# Deploy state the repo must not hold — see docs/GENIE_STANDARDS.md §4.
FORBIDDEN_KEYS = ("space_id", "genie_space_id")


def check(path: str = CONFIG) -> list[str]:
    """Every problem with the declaration, so one run lists all of them."""
    problems: list[str] = []
    if not os.path.exists(path):
        return [f"{path} does not exist"]

    root = os.path.dirname(path)
    with open(path, encoding="utf-8") as f:
        space = yaml.safe_load(f) or {}

    if not space.get("title"):
        problems.append(f"{path}: 'title' is missing — it is the deployed space's identity")
    if not space.get("warehouse_id"):
        problems.append(f"{path}: 'warehouse_id' is missing")
    if not space.get("data_sources"):
        problems.append(
            f"{path}: 'data_sources' is missing — a space with no tables answers nothing"
        )

    for key in FORBIDDEN_KEYS:
        if key in space:
            problems.append(
                f"{path}: remove '{key}'. Deploy state does not belong in the repo — "
                "the space is resolved by title (docs/GENIE_STANDARDS.md §4)"
            )

    for field in ("description_file", "instructions_file"):
        ref = space.get(field)
        if ref and not os.path.exists(os.path.join(root, ref)):
            problems.append(f"{path}: {field} {ref!r} does not resolve to a file")

    return problems


def main() -> None:
    problems = check()
    if problems:
        for p in problems:
            print(f"ERROR: {p}")
        sys.exit(1)
    print(f"✓ {CONFIG} valid")


if __name__ == "__main__":
    main()
