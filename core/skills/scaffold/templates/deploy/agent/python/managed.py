"""Reconcile the live Agent Bricks supervisor agent to src/managed/agent.yml.

The Beta REST surface is /api/2.1/supervisor-agents. It is called through the
SDK's raw api_client rather than a typed service, so a runtime whose
databricks-sdk predates the Beta still works — only the path has to be right.

Identity is the DISPLAY NAME, not an id. The repo therefore holds no deploy
state: the same commit creates the agent in a workspace that has none, and
updates it in one that does. The endpoint name (mas-<hex>-endpoint) is assigned
by Databricks at create time and printed at the end, because the API repo that
calls this agent needs it.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import yaml

API = "/api/2.1/supervisor-agents"

# Fields the update_mask may carry. Tools are a separate sub-resource.
AGENT_FIELDS = ("display_name", "description", "instructions")

_PLACEHOLDER = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def substitute(node: Any, variables: dict[str, str]) -> Any:
    """Replace ${name} throughout a loaded YAML tree.

    Fails on an unknown name rather than leaving the literal in place — a
    ${genie_space_id} that reached the API would be accepted as a space id, and
    the agent would deploy green with a tool that answers nothing.
    """
    if isinstance(node, dict):
        return {k: substitute(v, variables) for k, v in node.items()}
    if isinstance(node, list):
        return [substitute(v, variables) for v in node]
    if isinstance(node, str):

        def one(m: "re.Match[str]") -> str:
            name = m.group(1)
            if name not in variables:
                raise KeyError(
                    f"agent.yml references ${{{name}}}, which was not passed as --var"
                )
            return variables[name]

        return _PLACEHOLDER.sub(one, node)
    return node


def load_spec(spec_dir: str, variables: dict[str, str]) -> dict[str, Any]:
    """Read src/managed/ into one fully-substituted spec."""
    root = os.path.join(spec_dir, "managed")
    with open(os.path.join(root, "agent.yml"), encoding="utf-8") as fh:
        spec = substitute(yaml.safe_load(fh), variables)

    instructions_file = spec.pop("instructions_file")
    with open(os.path.join(root, instructions_file), encoding="utf-8") as fh:
        # Byte-verbatim: no strip(), no reflow. The instructions are compared
        # against the live agent's, so tidying makes a no-op deploy a change.
        spec["instructions"] = fh.read()

    check(spec)
    return spec


def check(spec: dict[str, Any]) -> None:
    """Validate the spec without touching the network. Also run by validate.py."""
    for field in ("display_name", "description", "instructions"):
        if not str(spec.get(field, "")).strip():
            raise ValueError(f"agent.yml: {field} is empty")

    tools = spec.get("tools") or []
    if not tools:
        raise ValueError("agent.yml: at least one tool is required")

    seen: set[str] = set()
    for tool in tools:
        tool_id = tool.get("tool_id")
        if not tool_id:
            raise ValueError("agent.yml: every tool needs a tool_id")
        if tool_id in seen:
            raise ValueError(f"agent.yml: duplicate tool_id {tool_id!r}")
        seen.add(tool_id)
        if not tool.get("tool_type"):
            raise ValueError(f"agent.yml: tool {tool_id!r} has no tool_type")

    for leftover in _PLACEHOLDER.findall(json.dumps(spec)):
        raise ValueError(f"agent.yml: ${{{leftover}}} survived substitution")


def _subset(declared: Any, live: Any) -> bool:
    """Is `declared` satisfied by `live`, ignoring fields the server adds?

    A genie_space declared as {"id": ...} comes back as {"id": ..., "space_id": ...}.
    Strict equality would call that drift and, because a tool spec is immutable,
    delete and recreate the tool on every single deploy.
    """
    if isinstance(declared, dict):
        if not isinstance(live, dict):
            return False
        return all(_subset(v, live.get(k)) for k, v in declared.items())
    return declared == live


# ── the reconciler ──────────────────────────────────────────────────────────


class Reconciler:
    def __init__(self, api, dry_run: bool = False) -> None:
        self._api = api
        self.dry_run = dry_run

    def _do(self, method: str, path: str, body: dict | None = None) -> dict:
        if self.dry_run and method != "GET":
            print(f"      [dry-run] {method} {path}")
            return {}
        return self._api.do(method, path, body=body) or {}

    def find_agent(self, display_name: str) -> dict | None:
        listed = self._api.do("GET", API) or {}
        for agent in listed.get("supervisor_agents") or []:
            if agent.get("display_name") == display_name:
                return agent
        return None

    def apply(self, spec: dict[str, Any]) -> dict:
        display_name = spec["display_name"]
        agent = self.find_agent(display_name)

        if agent is None:
            print(f"── Creating supervisor agent {display_name!r}")
            body = {f: spec[f] for f in AGENT_FIELDS}
            agent = self._do("POST", API, body)
            if self.dry_run:
                return {"display_name": display_name, "endpoint_name": "(dry-run)"}
        else:
            name = agent["name"]  # supervisor-agents/{id}
            drift = [f for f in AGENT_FIELDS if agent.get(f) != spec[f]]
            if drift:
                print(f"── Updating {display_name!r}: {', '.join(drift)}")
                # update_mask is a QUERY parameter, not a body field, and only
                # the fields it names are applied.
                body = {f: spec[f] for f in AGENT_FIELDS}
                path = f"/api/2.1/{name}?update_mask={','.join(drift)}"
                agent = self._do("PATCH", path, body) or agent
            else:
                print(f"── {display_name!r} already matches the spec")

        self._reconcile_tools(agent["name"], spec["tools"])
        return agent

    def _create_tool(self, base: str, tool_id: str, body: dict) -> None:
        # tool_id is a QUERY parameter on create, not a body field — sending it
        # in the body is rejected with "Field 'tool_id' is required".
        self._do("POST", f"{base}?tool_id={tool_id}", body)

    def _reconcile_tools(self, agent_name: str, desired: list[dict]) -> None:
        base = f"/api/2.1/{agent_name}/tools"
        listed = self._api.do("GET", base) or {}
        # The list response omits some spec bodies, so read each tool in full —
        # otherwise every tool looks changed and every deploy rewrites them.
        live = {}
        for stub in listed.get("tools") or []:
            live[stub["tool_id"]] = (
                self._api.do("GET", f"{base}/{stub['tool_id']}") or stub
            )

        for tool in desired:
            tool_id = tool["tool_id"]
            body = {k: v for k, v in tool.items() if k != "tool_id"}
            current = live.pop(tool_id, None)

            if current is None:
                print(f"   + tool {tool_id} ({tool['tool_type']})")
                self._create_tool(base, tool_id, body)
                continue

            # Only description is mutable: "To change immutable fields such as
            # tool type, spec, or tool ID, delete the tool and recreate it."
            # So repointing a tool at a new Genie space is a replace, not a patch.
            spec_drift = [
                k
                for k, v in body.items()
                if k != "description" and not _subset(v, current.get(k))
            ]
            if spec_drift:
                print(
                    f"   ↻ tool {tool_id} (immutable field changed: {', '.join(spec_drift)})"
                )
                self._do("DELETE", f"{base}/{tool_id}")
                self._create_tool(base, tool_id, body)
            elif current.get("description") != body.get("description"):
                print(f"   ~ tool {tool_id} (description)")
                self._do(
                    "PATCH",
                    f"{base}/{tool_id}?update_mask=description",
                    {
                        "tool_type": body["tool_type"],
                        "description": body["description"],
                    },
                )
            else:
                print(f"   = tool {tool_id}")

        # Whatever is left was not declared — including anything added in the UI,
        # whose ids embed the target (vsi-<catalog>-<schema>-<index>) rather than
        # using the stable logical ids above.
        for orphan in live:
            print(f"   - tool {orphan} (not in agent.yml)")
            self._do("DELETE", f"{base}/{orphan}")


def deploy(
    api, spec_dir: str, variables: dict[str, str], dry_run: bool = False
) -> dict:
    spec = load_spec(spec_dir, variables)
    agent = Reconciler(api, dry_run=dry_run).apply(spec)

    endpoint = agent.get("endpoint_name", "(unknown)")
    print()
    print(f"   agent     {agent.get('name', '(dry-run)')}")
    print(f"   endpoint  {endpoint}")
    print()
    # Databricks assigns the endpoint name at create time, so it cannot be
    # predicted — any API repo that calls this agent has to be told what it is.
    print("   If this is a new agent, set the calling API's mas_endpoint variable")
    print(f"   for this target to: {endpoint}")
    return agent
