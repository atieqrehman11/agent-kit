"""Create / update an Agent Bricks Multi-Agent Supervisor from config — scripted.

This is the script equivalent of building a supervisor agent in the Databricks
Agents-tab UI: it reads supervisor/supervisor.yml (+ instructions.md), creates (or
updates) the supervisor with those instructions, attaches the listed tools, and prints
the working query URL — the same URL the UI would give you.

Run with a workspace configured (DATABRICKS_HOST + DATABRICKS_TOKEN, or a CLI profile):

    ./deploy.sh
    #  or:  python src/deploy.py --config supervisor/supervisor.yml

Agent Bricks + the `supervisor_agents` SDK service are in Preview and move quickly —
confirm the service/tool-type names against your installed databricks-sdk:
https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor
"""

from __future__ import annotations

import argparse
import os

import yaml
from databricks.sdk import WorkspaceClient


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_tool(spec: dict):
    """Map one config tool entry to an SDK Tool object. Import the type-specific
    classes lazily so a missing one gives a precise, actionable error rather than an
    obscure crash. Extend `builders` as you attach more tool types."""
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


def _print_working_url(w: WorkspaceClient, created) -> None:
    """Print the supervisor's working query URL (what the UI shows)."""
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
    args = ap.parse_args()

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
    agent = SupervisorAgent(
        display_name=cfg["display_name"],
        description=cfg.get("description", ""),
        instructions=instructions,
    )

    existing_id = cfg.get("supervisor_agent_id")
    if existing_id:
        print(f"==> updating supervisor {existing_id}")
        from google.protobuf.field_mask_pb2 import FieldMask

        created = w.supervisor_agents.update_supervisor_agent(
            name=f"supervisor-agents/{existing_id}",
            supervisor_agent=agent,
            update_mask=FieldMask(paths=["display_name", "description", "instructions"]),
        )
    else:
        print(f"==> creating supervisor {cfg['display_name']!r}")
        created = w.supervisor_agents.create_supervisor_agent(supervisor_agent=agent)
        new_id = created.supervisor_agent_id or created.id
        if new_id:
            cfg["supervisor_agent_id"] = new_id
            with open(args.config, "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, sort_keys=False)
            print(f"    wrote supervisor_agent_id={new_id} back to {args.config}")

    sid = cfg.get("supervisor_agent_id") or created.supervisor_agent_id or created.id

    for spec in cfg.get("tools") or []:
        print(f"==> attaching tool {spec['id']} ({spec['type']})")
        w.supervisor_agents.create_tool(
            parent=f"supervisor-agents/{sid}",
            tool=_build_tool(spec),
            tool_id=spec["id"],
        )

    print("==> deployed")
    print(f"    supervisor id: {sid}")
    _print_working_url(w, created)


if __name__ == "__main__":
    main()
