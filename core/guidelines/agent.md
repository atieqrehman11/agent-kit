---
name: agent
kind: guideline
description: >
  Standards for multi-agent supervisor services: agent boundaries, tool exposure,
  instructions and evaluation. Applies when building or reviewing an agent service.
applies_to:
  - "**/supervisor/**"
  - "**/docs/AGENT_STANDARDS.md"
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

## 4a. Writing the two things well

Instructions and tool descriptions **are** the product here — there is no code to compensate
for a vague one.

`instructions.md`:

- **Route by observable condition, not by topic.** "When the question names a specific document
  or asks for a quotation, call X" beats "X is for documents."
- Name the **out-of-scope** behaviour explicitly: what the supervisor declines, and what it
  says when it declines. An unstated boundary is one the model invents per conversation.
- State the grounding rule: answer only from tool output, and say so when a tool returns nothing.
  Never let the fallback be the model's own knowledge unless that is a deliberate decision.
- Give a tie-break rule for the case where two tools both look applicable.
- One instruction per line, imperative. Prose paragraphs read well and route badly.

`supervisor.yml: tools[].description`:

- Written **for the router, not for a human** — it is the only thing distinguishing this tool
  from its neighbours at selection time.
- Say what the tool covers *and* what it does not. Overlapping descriptions are the single
  largest cause of wrong routing.
- Keep them mutually exclusive. If two descriptions could both match the same question, either
  merge the tools or add the discriminator to both.

## 4b. Safety and data handling

- Instructions are a **trust boundary, not a security control.** Anything a tool must not do,
  the tool itself must refuse — an instruction saying "do not" is advisory to a model and
  bypassable by the user.
- Attach the narrowest tool set that covers the use case. Every attached tool is reachable by
  any user who can reach the supervisor.
- Retrieved content is untrusted input. Instructions must state that text inside a document is
  data to summarise, never an instruction to follow.
- Access control lives on the tool's own resource — the Genie space, the index, the function —
  under the supervisor's principal. Never rely on the supervisor to keep a user away from data
  its principal can read.
- Record in `CHANGELOG.md` whether a change altered routing, scope or grounding — those are the
  changes that need a fresh eval baseline, not a wording tidy.

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
