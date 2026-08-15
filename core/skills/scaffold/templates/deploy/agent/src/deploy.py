"""Create / update an Agent Bricks Multi-Agent Supervisor from supervisor/ config.

The supervisor is identified by name, "<display_name> [ENV]", in the workspace the SDK
authenticated to — no id is stored in the repo. See docs/AGENT_STANDARDS.md §3a.

    ./deploy.sh                     # dev
    ./deploy.sh --env stg

Agent Bricks + `supervisor_agents` are Preview; confirm the service and tool-type names
against your installed databricks-sdk.
https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor
"""

from __future__ import annotations

import argparse
import os

import yaml
from databricks.sdk import WorkspaceClient
from validate import check

ENVS = ("dev", "stg", "prod")


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def target_name(display_name: str, env: str) -> str:
    """Every environment is suffixed, prod included — one rule, no exception."""
    return f"{display_name} [{env.upper()}]"


def _agent_id(obj):
    return getattr(obj, "supervisor_agent_id", None) or getattr(obj, "id", None)


def _resolve_existing(w, name: str):
    """The supervisor with this name, or None. Refuses on duplicates."""
    lister = getattr(w.supervisor_agents, "list_supervisor_agents", None)
    if lister is None:
        raise SystemExit(
            "This databricks-sdk has no supervisor_agents.list_supervisor_agents. "
            "Deploy resolves the supervisor by name and cannot run without it — "
            "upgrade the SDK (see requirements.txt)."
        )
    matches = [a for a in (lister() or []) if getattr(a, "display_name", None) == name]
    if len(matches) > 1:
        raise SystemExit(
            f"{len(matches)} supervisors in this workspace are named {name!r}. Deploy "
            "refuses to guess which one is this repo's — delete or rename the extras."
        )
    return matches[0] if matches else None


def _build_tool(spec: dict):
    """One config tool entry -> an SDK Tool. Add a builder here for a new type."""
    from databricks.sdk.service import supervisoragents as sa

    ttype = spec["type"]
    desc = spec.get("description", "")

    def knowledge_assistant():
        return sa.Tool(
            tool_type="knowledge_assistant",
            description=desc,
            knowledge_assistant=sa.KnowledgeAssistant(
                knowledge_assistant_id=spec["knowledge_assistant_id"]
            ),
        )

    def genie_space():
        return sa.Tool(
            tool_type="genie_space",
            description=desc,
            genie_space=sa.GenieSpace(id=spec["genie_space_id"]),
        )

    builders = {
        "knowledge_assistant": knowledge_assistant,
        "genie_space": genie_space,
    }
    if ttype not in builders:
        raise ValueError(
            f"tool type {ttype!r} is not wired yet. Supported: {sorted(builders)}. "
            f"Add a builder in deploy.py._build_tool for it."
        )
    return builders[ttype]()


def _attach_tool(w, parent: str, spec: dict) -> None:
    """Attach the tool, updating it if that tool_id is already there."""
    tool = _build_tool(spec)
    try:
        w.supervisor_agents.create_tool(parent=parent, tool=tool, tool_id=spec["id"])
        return
    except Exception as exc:  # noqa: BLE001 — the SDK's conflict type is Preview-unstable
        # "already exists", not "exist" — the latter also matches "does not exist",
        # which would send a genuine not-found down the update path.
        if "already exists" not in str(exc).lower():
            raise
    updater = getattr(w.supervisor_agents, "update_tool", None)
    if updater is None:
        raise SystemExit(
            f"tool {spec['id']!r} already exists and this SDK has no "
            "supervisor_agents.update_tool to reconcile it. Upgrade the SDK, or "
            "detach the tool in the Agents tab and redeploy."
        )
    updater(name=f"{parent}/tools/{spec['id']}", tool=tool)


def _print_working_url(w: WorkspaceClient, created) -> None:
    host = w.config.host.rstrip("/")
    for attr in ("endpoint_url", "query_url", "url"):
        val = getattr(created, attr, None)
        if val:
            print(f"    working URL: {val}")
            return
    endpoint = getattr(created, "endpoint_name", None) or getattr(created, "name", None)
    if endpoint:
        print(f"    working URL: {host}/serving-endpoints/{endpoint}/invocations")
    else:
        print(f"    created object: {created}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Deploy the multi-agent supervisor.")
    ap.add_argument("--config", default="supervisor/supervisor.yml")
    ap.add_argument(
        "--env",
        default="dev",
        choices=ENVS,
        help="target environment — the name suffix; the workspace comes from "
        "DATABRICKS_HOST / the CLI profile",
    )
    args = ap.parse_args()

    problems = check(args.config)
    if problems:
        raise SystemExit("\n".join([f"ERROR: {p}" for p in problems] + ["Refusing to deploy."]))

    root = os.path.dirname(os.path.abspath(args.config))
    cfg = _load(args.config)
    instructions = (
        open(os.path.join(root, cfg["instructions_file"]), encoding="utf-8").read().strip()
    )

    try:
        from databricks.sdk.service.supervisoragents import SupervisorAgent
    except ImportError as exc:
        raise SystemExit(
            "This databricks-sdk has no `supervisoragents` service. Upgrade the SDK "
            "(see requirements.txt) — Agent Bricks Multi-Agent Supervisor is Preview."
        ) from exc

    w = WorkspaceClient()
    name = target_name(cfg["display_name"], args.env)
    print(f"==> target {name!r} in {w.config.host}")

    agent = SupervisorAgent(
        display_name=name,
        description=cfg.get("description", ""),
        instructions=instructions,
    )

    existing = _resolve_existing(w, name)
    if existing:
        sid = _agent_id(existing)
        print(f"==> updating supervisor {sid}")
        from google.protobuf.field_mask_pb2 import FieldMask

        deployed = w.supervisor_agents.update_supervisor_agent(
            name=f"supervisor-agents/{sid}",
            supervisor_agent=agent,
            update_mask=FieldMask(paths=["display_name", "description", "instructions"]),
        )
    else:
        print("==> creating supervisor (no existing one with that name)")
        deployed = w.supervisor_agents.create_supervisor_agent(supervisor_agent=agent)
        sid = _agent_id(deployed)

    for spec in cfg.get("tools") or []:
        print(f"==> attaching tool {spec['id']} ({spec['type']})")
        _attach_tool(w, f"supervisor-agents/{sid}", spec)

    print("==> deployed")
    print(f"    env:           {args.env}")
    print(f"    supervisor id: {sid}")
    _print_working_url(w, deployed)


if __name__ == "__main__":
    main()
