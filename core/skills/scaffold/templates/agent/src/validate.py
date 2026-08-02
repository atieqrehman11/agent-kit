"""Check supervisor/supervisor.yml. No credentials, no network — CI's first stage.

    python src/validate.py

deploy.py calls check() too, so "valid" has one definition.
"""

from __future__ import annotations

import os
import sys

import yaml

CONFIG = "supervisor/supervisor.yml"

# Deploy state the repo must not hold — see docs/AGENT_STANDARDS.md §3a.
FORBIDDEN_KEYS = ("supervisor_agent_id", "supervisor_id", "agent_id")


def check(path: str = CONFIG) -> list[str]:
    """Every problem with the declaration, so one run lists all of them."""
    problems: list[str] = []
    if not os.path.exists(path):
        return [f"{path} does not exist"]

    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    if not cfg.get("display_name"):
        problems.append(
            f"{path}: 'display_name' is missing — it is the deployed supervisor's identity"
        )

    ref = cfg.get("instructions_file")
    if not ref:
        problems.append(f"{path}: 'instructions_file' is missing")
    elif not os.path.exists(os.path.join(os.path.dirname(path), ref)):
        problems.append(f"{path}: instructions_file {ref!r} does not resolve to a file")

    for key in FORBIDDEN_KEYS:
        if key in cfg:
            problems.append(
                f"{path}: remove '{key}'. Deploy state does not belong in the repo — "
                "the supervisor is resolved by name (docs/AGENT_STANDARDS.md §3a)"
            )

    for i, tool in enumerate(cfg.get("tools") or []):
        missing = [k for k in ("id", "type", "description") if not tool.get(k)]
        if missing:
            problems.append(f"{path}: tools[{i}] is missing {', '.join(missing)}")

    return problems


def main() -> None:
    problems = check()
    if problems:
        for p in problems:
            print(f"ERROR: {p}")
        sys.exit(1)
    with open(CONFIG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    print(f"✓ {CONFIG} valid — {len(cfg.get('tools') or [])} tool(s)")


if __name__ == "__main__":
    main()
