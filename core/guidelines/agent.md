---
name: agent
kind: guideline
description: >
  Standards for multi-agent supervisor services: agent boundaries, tool exposure,
  instructions and evaluation. Applies when building or reviewing an agent service.
---

# Agent Standards — __ORG_PREFIX__Multi-Agent Supervisor Reference

Standard for the `agent` repo type: a Databricks **Agent Bricks Multi-Agent Supervisor**
created via the `supervisor_agents` **SDK** — the scripted equivalent of building a
supervisor in the Agents-tab UI. There is no DAB bundle and (for now) no CI/CD.

The idea: **standardize how we stamp out supervisors.** To spin up a new one you provide
only two things — **instructions** and a **list of tools to attach** — and one script does
what the UI does, returning a working query URL. The **repo is authoritative**: the
supervisor is (re)deployed *from* these files.

---

## 1. Canonical layout

```
supervisor/
├── supervisor.yml     the DEFINITION — display_name, description, tools list,
│                       supervisor_agent_id (written back by deploy on first create)
└── instructions.md    the supervisor's routing instructions (prose)
src/deploy.py          create/update the supervisor + attach tools; prints the URL
deploy.sh              one-shot: pip install + run deploy.py
CHANGELOG.md           version → date → eval baseline → what changed
AGENT_STANDARDS.md     this file
```

No per-agent Python and no hand-written tool loop — the supervisor's reasoning and
tool-routing are managed by Agent Bricks. You supply configuration, not code.

---

## 2. The two things you edit

- **`instructions.md`** — how the supervisor should behave and route: for each tool, when
  to call it; grounding and out-of-scope rules; tone. Sent verbatim as the supervisor's
  instructions.
- **`supervisor.yml: tools`** — the list of tools/subagents to attach. Each entry:
  - `id` — a stable key for the tool within this supervisor
  - `type` — the tool type (e.g. `knowledge_assistant`, `genie_space`)
  - `description` — what it does; the supervisor uses this to decide when to route to it
  - the type-specific reference (e.g. `knowledge_assistant_id`, `genie_space_id`)

Everything else (display name, description) is a couple of scalar fields at the top.

---

## 3. Deploy flow (`src/deploy.py`)

`deploy.py` uses the Databricks SDK:

1. Build a `SupervisorAgent(display_name, description, instructions)`.
2. **Create** it (`w.supervisor_agents.create_supervisor_agent`) when `supervisor_agent_id`
   is empty, and write the new id back to `supervisor.yml`; **update** it when the id is
   set. Commit the id so later runs target the same supervisor (idempotent).
3. **Attach** each configured tool with `w.supervisor_agents.create_tool(...)`, building the
   type-specific `Tool` object in `_build_tool` (extend that function to support more tool
   types).
4. **Print the working query URL** — the same URL the Agents-tab UI would show.

```
./deploy.sh          # needs DATABRICKS_HOST + DATABRICKS_TOKEN (or a CLI profile)
```

> Agent Bricks and the `supervisor_agents` SDK service are in **Preview** and move quickly.
> Confirm the service name, the `SupervisorAgent`/`Tool` classes, the tool-type field names,
> and the update method against your installed `databricks-sdk`; `deploy.py` fails with a
> clear message if the service or a tool type is missing.
> https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor

---

## 4. Adding a tool type

`deploy.py._build_tool` has a small registry mapping a config `type` to an SDK `Tool`
builder. `knowledge_assistant` and `genie_space` ship wired. To attach another kind
(another agent, a UC function, an MCP server, …), add a builder that constructs the right
`Tool(...)` for your SDK version and list the type in `supervisor.yml`.

---

## 5. Versioning & the eval loop

- Keep `CHANGELOG.md`: version → date → eval baseline → what changed, one row per deploy.
- The loop: **edit `supervisor/` → deploy → run `evaluation/` → record the baseline**.
  Scaffold the eval area with `{{cmd:eval:new}}` and point the spec at the supervisor's
  query URL.

---

## 6. Moving to CI/CD later

Deployment is a plain script by design while the path is being proven. When the shared
controller supports supervisor deploys, wrap `deploy.py` in the CI runner (Databricks SDK
auth) — `supervisor/` and `deploy.py` do not change.
