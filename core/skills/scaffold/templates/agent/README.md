# TPLVAR_DISPLAY_NAME

TPLVAR_DESCRIPTION

**Type:** `agent` — a **Multi-Agent Supervisor** created via the Databricks
`supervisor_agents` SDK. Deployment is **script-driven** (`./deploy.sh`) — the scripted
equivalent of building a supervisor in the Agents-tab UI. To spin up a supervisor you
edit two things — its **instructions** and a **list of tools to attach** — then deploy.

## Layout

```
supervisor/supervisor.yml   the definition — display_name, description, tools list,
                            supervisor_agent_id (written back on first create)
supervisor/instructions.md  the supervisor's routing instructions (prose)
src/deploy.py               create/update the supervisor + attach tools; prints the URL
deploy.sh                   one-shot: pip install + run deploy.py
docs/                       standards (AGENT_STANDARDS.md, PYTHON_STANDARDS.md)
```

## Spin it up

1. Write the routing instructions in [`supervisor/instructions.md`](supervisor/instructions.md).
2. In [`supervisor/supervisor.yml`](supervisor/supervisor.yml), set `display_name` /
   `description` and fill the `tools` list — each entry is a `type` (e.g.
   `knowledge_assistant`, `genie_space`), a `description`, and the tool's id.
3. Deploy (needs `DATABRICKS_HOST` + `DATABRICKS_TOKEN`):

   ```
   ./deploy.sh
   ```

   It creates the supervisor (or updates it if `supervisor_agent_id` is set), attaches the
   tools, and prints the **working query URL** — the same URL the UI gives you. The new
   `supervisor_agent_id` is written back to `supervisor.yml`; commit it so later runs update
   the same supervisor.

Full guidance: [`docs/AGENT_STANDARDS.md`](docs/AGENT_STANDARDS.md).

## Standards

- [`docs/PYTHON_STANDARDS.md`](docs/PYTHON_STANDARDS.md) — code style (PEP 8, type hints, Ruff).
- [`docs/AGENT_STANDARDS.md`](docs/AGENT_STANDARDS.md) — how the supervisor is built and deployed.

Run `ruff check` and `ruff format` before committing.

> Agent Bricks + the `supervisor_agents` SDK are in Preview — confirm the service and
> tool-type names against your installed `databricks-sdk`. CI/CD is deferred; deployment is
> script-driven today.
