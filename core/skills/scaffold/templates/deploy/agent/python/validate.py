"""Check src/managed/ without credentials or network — CI's first stage.

    PYTHONPATH=python python python/validate.py

deploy_agent.py calls the same check(), so "valid" has one definition. This
validates the DECLARATION only. Whether a deploy would delete a tool from the
live agent is a separate question that needs the workspace, and
`./run_local.sh plan` answers it.
"""

from __future__ import annotations

import sys

from managed import check, load_spec

# Stand-ins for the per-target values databricks.yml supplies. Their values are
# never used here — substitution just has to resolve so the shape can be checked.
# Add one entry per ${name} that agent.yml references.
PROBE_VARS = {
    "display_name": "validate-probe",
    "genie_space_id": "0" * 32,
    "vector_search_index": "probe.probe.probe_index",
}


def main() -> int:
    try:
        spec = load_spec("src", PROBE_VARS)
        check(spec)
    except (KeyError, ValueError, OSError) as err:
        print(f"✗ {err}", file=sys.stderr)
        return 1

    tools = ", ".join(f"{t['tool_id']} ({t['tool_type']})" for t in spec["tools"])
    print(
        f"✓ src/managed/ is valid — {len(spec['instructions'])} chars of instructions"
    )
    print(f"  tools: {tools}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
