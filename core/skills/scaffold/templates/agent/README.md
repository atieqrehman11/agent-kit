# TPLVAR_DISPLAY_NAME

TPLVAR_DESCRIPTION

**Type:** `agent` — a **Multi-Agent Supervisor** created via the Databricks
`supervisor_agents` SDK. Deployment is **script-driven** (`./deploy.sh`) — the scripted
equivalent of building a supervisor in the Agents-tab UI. To spin up a supervisor you
edit two things — its **instructions** and a **list of tools to attach** — then deploy.

## Deployment

| Target | How |
|---|---|
| **local (dev)** | `./deploy.sh` — reconcile the supervisor + attach its tools |
| **stg / prod** | merge to the `stg` / `prod` branch — CI runs `src/deploy.py --env <branch>` |

**No id is stored in this repo.** The supervisor is found by name,
`"<display_name> [ENV]"`, in the workspace `DATABRICKS_HOST` points at — one match is
updated, none creates it, several refuse. See [`docs/AGENT_STANDARDS.md`](docs/AGENT_STANDARDS.md) §3a.

## Layout

```
supervisor/supervisor.yml   the definition — display_name, description, tools list
supervisor/instructions.md  the supervisor's routing instructions (prose)
src/validate.py             check supervisor.yml — no credentials, no network
src/deploy.py               reconcile the supervisor + attach tools; prints the URL
deploy.sh                   one-shot: pip install + run deploy.py (dev)
.gitlab-ci.yml              two jobs, each one line: run validate.py, run deploy.py
docs/                       standards (AGENT_STANDARDS.md, PYTHON_STANDARDS.md)
```

Check it before pushing — no credentials needed, same check CI runs first:

```
python src/validate.py
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

   It creates the supervisor named `<display_name> [DEV]` — or updates it if it is already
   there — attaches the tools, and prints the **working query URL**, the same URL the UI
   gives you. Nothing is written back to `supervisor.yml`.

4. For stg / prod, set `DATABRICKS_HOST` + `DATABRICKS_TOKEN` in GitLab CI/CD variables
   scoped to each branch, then merge to `stg` / `prod` and run the manual deploy job.

Full guidance: [`docs/AGENT_STANDARDS.md`](docs/AGENT_STANDARDS.md).

## Standards

- [`docs/PYTHON_STANDARDS.md`](docs/PYTHON_STANDARDS.md) — code style (PEP 8, type hints, Ruff).
- [`docs/AGENT_STANDARDS.md`](docs/AGENT_STANDARDS.md) — how the supervisor is built and deployed.

Run `ruff check` and `ruff format` before committing.

> Agent Bricks + the `supervisor_agents` SDK are in Preview — confirm the service, tool-type
> and list-method names against your installed `databricks-sdk`. `deploy.py` fails with a
> named error rather than a stack trace when one of them is missing.
