"""Deploy the TPLVAR_SLUG supervisor agent. Runs as the bundle's only job task.

    python python/deploy_agent.py --spec-dir src --var display_name=...

A supervisor agent has no DAB resource type, and the CI/CD controller reaches
project code only through `bundle run` on a resource — so the deploy has to BE a
resource. That is why this script runs as a job task: `bundle deploy` uploads
src/ and python/ to the workspace, and `bundle run deploy_agent` executes it
there. dev runs the same job the controller runs, so there is one deploy path.

Auth comes from the runtime: in the job it is the bundle's run_as principal, and
locally it is your ~/.databrickscfg profile.
"""

from __future__ import annotations

import argparse
import os
import sys


def import_managed(spec_dir: str):
    """Import the sibling module by path.

    A serverless spark_python_task exec()s this file rather than importing it, so
    __file__ is undefined and the script's own directory is not on sys.path.
    --spec-dir is an absolute workspace path (${workspace.file_path}/src), and
    python/ is its sibling, so that is what locates the module.
    """
    python_dir = os.path.join(os.path.dirname(os.path.abspath(spec_dir)), "python")
    if python_dir not in sys.path:
        sys.path.insert(0, python_dir)
    import managed

    return managed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec-dir", default="src")
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="substituted into agent.yml; repeatable",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="report changes, apply none"
    )
    return parser.parse_args(argv)


def parse_vars(pairs: list[str]) -> dict[str, str]:
    variables = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"--var expects NAME=VALUE, got {pair!r}")
        name, _, value = pair.partition("=")
        variables[name] = value
    return variables


def reject_placeholders(variables: dict[str, str]) -> None:
    """Stop a TODO_SET_* from reaching the API.

    databricks.yml carries these for stg and prod until the upstream resource
    exists. The API would accept "TODO_SET_STG_GENIE_SPACE_ID" as a space id and
    the agent would deploy green with a tool that answers nothing.
    """
    unset = sorted(k for k, v in variables.items() if v.startswith("TODO_SET_"))
    if unset:
        raise SystemExit(
            "ERROR: these values are still placeholders in databricks.yml for this "
            f"target: {', '.join(unset)}. Set them before deploying."
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    variables = parse_vars(args.var)
    reject_placeholders(variables)

    from databricks.sdk import WorkspaceClient

    managed = import_managed(args.spec_dir)

    managed.deploy(
        WorkspaceClient().api_client,
        spec_dir=args.spec_dir,
        variables=variables,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    # Only raise on failure. The serverless task runner reports ANY SystemExit as
    # a failed task — including SystemExit(0) — so a successful deploy that
    # exited explicitly would be reported as a failure.
    _rc = main()
    if _rc:
        raise SystemExit(_rc)
