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
supervisor in the Agents-tab UI. There is no DAB bundle; CI deploys by running the same
script (§3, §6).

The idea: **standardize how we stamp out supervisors.** To spin up a new one you provide
only two things — **instructions** and a **list of tools to attach** — and one script does
what the UI does, returning a working query URL. The **repo is authoritative**: the
supervisor is (re)deployed *from* these files.

---

## 1. Canonical layout

```
supervisor/
├── supervisor.yml     the DEFINITION — display_name, description, tools list
└── instructions.md    the supervisor's routing instructions (prose)
src/validate.py        check supervisor.yml — no credentials, no network
src/deploy.py          reconcile the supervisor + attach tools; prints the URL
deploy.sh              one-shot: pip install + run deploy.py (dev)
.gitlab-ci.yml         two jobs, each one line: run validate.py, run deploy.py
CHANGELOG.md           version → date → eval baseline → what changed
AGENT_STANDARDS.md     this file
```

> **CI holds no logic of its own** — each stage runs one of these scripts, so every check
> that gates a deploy also runs on a laptop. `deploy.py` calls the same `validate.check()`
> before touching a workspace.

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

1. Resolve the target name: `"<display_name> [ENV]"` for the `--env` given (§3a).
2. Build a `SupervisorAgent(display_name, description, instructions)`.
3. **Resolve** the existing supervisor by listing and matching that name. Exactly one
   match → **update** it (`update_supervisor_agent`); none → **create** it
   (`create_supervisor_agent`); more than one → **fail**, rather than guess which
   supervisor belongs to this repo.
4. **Attach** each configured tool with `w.supervisor_agents.create_tool(...)`, falling back
   to `update_tool` when the `tool_id` is already attached, so a redeploy converges instead
   of erroring. Build the type-specific `Tool` object in `_build_tool` (extend that function
   to support more tool types).
5. **Print the working query URL** — the same URL the Agents-tab UI would show.

```
./deploy.sh                # dev; needs DATABRICKS_HOST + DATABRICKS_TOKEN (or a CLI profile)
./deploy.sh --env stg      # normally CI's job, not a laptop's
```

---

## 3a. Identity and environments — declare, don't record

**The repo stores no id for the deployed supervisor.** `supervisor.yml` declares what should
exist; it does not record what does. Identity is two axes together:

| Axis | Source |
|---|---|
| Which workspace | `DATABRICKS_HOST` / the CLI profile the deploy authenticated with |
| Which supervisor in it | the name `"<display_name> [ENV]"`, from config + `--env` |

Every environment is suffixed, prod included — one rule, no exception, so the name is
derivable from `(config, env)` alone in CI as on a laptop.

**Why not store the id?** CI cannot hold it. A runner checks out fresh, reads an empty id,
creates a *new* supervisor, and discards the write-back — one more per pipeline run. A field
per environment does not help: the id is an output of a deploy, and CI's only place to put an
output is a commit, which is a race.

Two consequences:

- **`display_name` is the identity.** Renaming it does not rename the deployed supervisor;
  the next deploy creates a new one under the new name. Clean up the old one yourself.
- **Duplicate names are a hard error** — deploy refuses rather than silently retargeting
  someone else's resource.

Same model as a DAB target: declarative identity plus a per-target workspace, no deploy state
in git. `genie` repos follow it by space title; see `GENIE_STANDARDS.md`.

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

## 4c. Tools that do things

A read-only tool that routes badly returns a wrong answer. A **side-effecting** tool that routes
badly writes, sends, refunds or deletes — and no instruction reliably prevents it, because §4b's
first rule applies hardest here: instructions are advisory.

**Always:**

- **Classify every tool read-only or side-effecting** in its `supervisor.yml` `description`,
  before attaching it. If nobody can say which it is, it is not ready to attach.
- **Prefer proposing to acting.** A tool that returns a draft for a human to apply removes this
  whole class of risk, and is usually what the use case actually needed.
- **Scope the principal, not the prompt.** A tool that *can* write to everything eventually will.

**Any side-effecting tool that reaches real data or real users also needs:**

- **Confirmation in the tool**, restating the resolved parameters — not in the instructions, and
  not a sentence the supervisor is asked to emit.
- **An audit record** per invocation: who asked, resolved parameters, what changed. The
  supervisor's transcript records what was *said*, not what was committed.
- **Idempotency, or a caller-supplied key** the tool deduplicates on. A retried turn, a duplicate
  route or a rephrasing must not double-apply.

## 5. Versioning & the eval loop

- Keep `CHANGELOG.md`: version → date → eval baseline → what changed, one row per deploy.
- The loop: **edit `supervisor/` → deploy → run `evaluation/` → record the baseline**.
  Scaffold the eval area with `{{cmd:eval:new}}` and point the spec at the supervisor's
  query URL.

**Instructions and tool descriptions are the product (§4a), so editing them is a behaviour change
with no compile step and no test to break.** The eval set is the only thing between a routing
tweak and a silent regression nobody re-checked.

- **Cover routing explicitly.** The common failure is not a bad answer — it is the right answer
  from the wrong tool, or two tools both firing. Assert *which tool answered*.
- **Cover the boundary**: an out-of-scope question is declined per §4a, and a tool returning
  nothing produces a stated "I don't know" rather than a fallback to model knowledge.
- **Cover injection**: a tool result saying "ignore your instructions" is reported as content.
- **The gate:** a change to `instructions.md`, a tool `description`, or the attached tool list
  requires a fresh eval run before merge, with the pass rate at or above the `CHANGELOG.md`
  baseline. A deliberate trade records the new baseline and reason in the same commit.
- **One run is not a result.** Run the set repeatedly and record the pass rate; a case that
  passes intermittently is failing.

## 5a. Observability and cost

- **One correlation id per turn, propagated into every tool call.** Without it a wrong answer
  cannot be traced to the tool that produced it, and debugging by reading the final reply is
  guesswork.
- **Record per turn**: tools called and in what order, tokens in and out, per-tool and total
  latency. Routing defects show up here long before a user reports one.
- **Cap what can run away** — tools per turn, retries per tool, total turn latency — in
  configuration, not instructions. A routing loop between two tools is a cost incident, and a
  model asked politely to stop will not.
- **Tool output is logged at DEBUG, never INFO.**
- Alert on refusal rate, empty-tool-result rate and per-tool error rate.

---

## 6. Deployment

| Target | How |
|---|---|
| **local (dev)** | `./deploy.sh` — reconciles `"<display_name> [DEV]"` |
| **stg / prod** | merge to the `stg` / `prod` branch — CI runs `src/deploy.py --env <branch>`, manual-gated |

Auth is the default Databricks SDK chain (`DATABRICKS_HOST` + token, or a CLI profile). For
stg / prod those two variables are set **per branch** in GitLab CI/CD settings — the
workspace they point at is what separates the environments, since the repo stores no
per-environment id (§3a).

There is no shared-controller path: a supervisor is not a DAB resource, so nothing is
deployed by the bundle controller. If that changes, the wrapper changes and `supervisor/` +
`deploy.py` do not.

---

## Conformance

The audit checklist for this guideline lives beside it, in [`conformance/agent.md`](conformance/agent.md) — one file, one source of truth, loaded by whoever is auditing rather than by everyone who edits a file.
