---
name: agent
kind: guideline
description: >
  Standards for multi-agent supervisor services: agent boundaries, tool exposure,
  instructions and evaluation. Applies when building or reviewing an agent service.
applies_to:
  - "**/src/managed/**"
  - "**/python/deploy_agent.py"
  - "**/python/managed.py"
---

# Agent Standards — __ORG_PREFIX__Multi-Agent Supervisor Reference

Standard for the `agent` repo type: a Databricks **Agent Bricks Multi-Agent Supervisor**,
reconciled from configuration against `/api/2.1/supervisor-agents` — the scripted
equivalent of building a supervisor in the Agents-tab UI.

The idea: **standardize how we stamp out supervisors.** To spin up a new one you provide
only two things — **instructions** and a **list of tools to attach** — and one reconciler
does what the UI does, returning a working endpoint name. The **repo is authoritative**:
the supervisor is (re)deployed *from* these files, and anything changed in the UI is
overwritten on the next deploy.

---

## 1. Canonical layout

```
src/managed/
├── agent.yml           the DEFINITION — display_name, description, tools list
└── instructions.md     the routing instructions (prose, sent byte-verbatim)
python/
├── deploy_agent.py     the job task entry point
├── managed.py          the reconciler
└── validate.py         check agent.yml — no credentials, no network
resources/deploy.job.yml  the job that IS the deploy (§6)
databricks.yml         per-environment values, passed to the job as --var
run_resources.yml      lists deploy_agent — what makes the controller run it
docs/CHANGELOG.md      version → date → eval baseline → what changed
```

> **CI holds no logic of its own** — the validate stage runs `python/validate.py`, the same
> check `deploy_agent.py` runs before touching a workspace, so every gate also runs on a
> laptop.

No per-agent Python and no hand-written tool loop — the supervisor's reasoning and
tool-routing are managed by Agent Bricks. You supply configuration, not code.

---

## 2. The two things you edit

- **`src/managed/instructions.md`** — how the supervisor should behave and route: for each
  tool, when to call it; grounding and out-of-scope rules; tone. Sent **byte-verbatim** as
  the supervisor's instructions, and compared byte for byte against the live agent — so
  reflowing the file turns a no-op deploy into a content change.
- **`src/managed/agent.yml: tools`** — the list of tools/subagents to attach. Each entry:
  - `id` — a stable key for the tool within this supervisor
  - `type` — the tool type (e.g. `knowledge_assistant`, `genie_space`)
  - `description` — what it does; the supervisor uses this to decide when to route to it
  - the type-specific reference (e.g. `knowledge_assistant_id`, `genie_space_id`)

Everything else (display name, description) is a couple of scalar fields at the top.

---

## 3. Reconcile flow (`python/managed.py`)

The REST surface is `/api/2.1/supervisor-agents`, called through the SDK's **raw
`api_client`** rather than a typed service — so a runtime whose `databricks-sdk` predates
the Beta still works, and only the path has to be right.

1. **Resolve** the agent by listing and matching `display_name` (§3a). None → **create**;
   one → **patch** only the fields that actually drifted.
2. **Reconcile tools by `tool_id`.** Read each live tool *in full* — the list response omits
   some spec bodies, so comparing against the list alone makes every tool look changed and
   rewrites them on every deploy.
3. **A tool spec is immutable.** Only `description` can be patched; changing anything else —
   repointing a tool at a different Genie space, say — is a **delete + recreate**, reusing
   the same stable `tool_id`.
4. **Anything not declared is deleted**, including tools added in the UI.
5. **Print the endpoint name** (`mas-<hex>-endpoint`). Databricks assigns it at create time,
   so it cannot be predicted, and any API repo calling this agent has to be told what it is.

Two comparison rules that are not obvious, and are why a naive reconciler churns:

- **Compare declared-is-a-subset-of-live, not equality.** A `genie_space` declared as
  `{"id": ...}` comes back as `{"id": ..., "space_id": ...}`. Strict equality reads the
  server-added field as drift and, because the spec is immutable, deletes and recreates the
  tool on *every single deploy*.
- **`update_mask` is a query parameter, not a body field**, and only the fields it names are
  applied. Likewise `tool_id` on create is a query parameter — sending it in the body is
  rejected with "Field 'tool_id' is required".

```
./run_local.sh             # validate only — no credentials, no network
./run_local.sh plan        # dry run against dev: what would change
./run_local.sh deploy      # bundle deploy -t dev, then bundle run
```

---

## 3a. Identity and environments — declare, don't record

**The repo stores no id for the deployed supervisor.** `agent.yml` declares what should
exist; it does not record what does. Identity is two axes together:

| Axis | Source |
|---|---|
| Which workspace | the bundle target's `workspace.host` (and its `run_as` principal) |
| Which supervisor in it | `display_name`, set per target in `databricks.yml` |

Suffix every environment, prod included — one rule, no exception, so the name is derivable
from the target alone.

**Why not store the id?** CI cannot hold it. The controller checks out fresh, reads an empty
id, creates a *new* supervisor, and discards the write-back — one more per pipeline run. A
field per environment does not help: the id is an output of a deploy, and CI's only place to
put an output is a commit, which is a race.

Two consequences:

- **`display_name` is the identity.** Renaming it does not rename the deployed supervisor;
  the next deploy creates a new one under the new name. Clean up the old one yourself.
- **Duplicate names are a hard error** — deploy refuses rather than silently retargeting
  someone else's resource.

Same model as any DAB target: declarative identity plus a per-target workspace, no deploy
state in git. A `genie` repo goes one better — DAB itself owns the space's identity through
the resource key; see [`genie`](./genie.md).

> Agent Bricks and the `supervisor_agents` SDK service are in **Preview** and move quickly.
> Confirm the service name, the `SupervisorAgent`/`Tool` classes, the tool-type field names,
> and the update method against your installed `databricks-sdk`; `deploy.py` fails with a
> clear message if the service or a tool type is missing.
> https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor

---

## 4. Adding a tool type

There is no registry to extend. `managed.py` passes a tool's body through to the API
unchanged apart from `tool_id`, so a new tool type is a new block in `agent.yml` and nothing
else:

```yaml
  - tool_id: some-index
    tool_type: vector_search_index      # the API's own type name
    vector_search_index:                # the type-specific spec, verbatim
      name: ${vector_search_index}
    description: >-
      When to route here, and what it does not cover.
```

Check the tool-type names and their spec fields against the workspace docs before adding
one — Agent Bricks is in Preview and these move. `validate.py` catches a missing `tool_id`
or `tool_type`, but it cannot know whether a spec body is the shape the API wants.

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

`agent.yml: tools[].description`:

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

- **Classify every tool read-only or side-effecting** in its `agent.yml` `description`,
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

- Keep `docs/CHANGELOG.md`: version → date → eval baseline → what changed, one row per deploy.
- The loop: **edit `src/managed/` → deploy → run `evaluation/` → record the baseline**.
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
  requires a fresh eval run before merge, with the pass rate at or above the `docs/CHANGELOG.md`
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

### The deploy IS a resource

A supervisor agent has **no DAB resource type**, and the shared CI/CD controller reaches
project code only through `bundle deploy` followed by `bundle run` on a resource. So the
deploy has to *be* a resource: the bundle's single resource is a **job** whose one task
runs the reconciler.

```
bundle deploy             uploads src/ + python/ to the workspace
bundle run deploy_agent   runs the reconciler there, against
                          /api/2.1/supervisor-agents
```

`run_resources.yml` lists `deploy_agent`, and that entry is what makes the controller
perform the second step. **Without it the deploy uploads a new spec, changes no agent, and
reports success.**

This is what keeps a supervisor on the same governed path as every other repo — one deploy
mechanism, no workspace token in CI, and dev running the identical job the controller runs.

| Target | How |
|---|---|
| **validate** | `./run_local.sh` — offline check of the spec |
| **plan** | `./run_local.sh plan` — what a deploy would add, change or **delete** |
| **local (dev)** | `./run_local.sh deploy` — `bundle deploy -t dev`, then `bundle run` |
| **stg** | merge to the `stg` branch — the controller deploys |
| **prod** | merge to `prod`, then press play in Build → Pipelines |

Never run `databricks bundle deploy -t stg|prod` by hand.

Auth comes from the runtime: inside the job it is the bundle's `run_as` principal, and
locally it is your `~/.databrickscfg` profile. There is no `DATABRICKS_TOKEN` in CI.

### Nothing in `src/` names an environment

`agent.yml` references `${...}` placeholders; `resources/deploy.job.yml` passes them as
`--var`, and `databricks.yml` sets them per target. A Genie space id is workspace-local, so
the dev value is never valid in stg. Two guards, both in `deploy_agent.py`:

- an unresolved `${name}` **fails** rather than reaching the API;
- a value still left as `TODO_SET_*` is **rejected** — the API would accept it as an id, and
  the agent would deploy green with a tool that answers nothing.

### Run `plan` before changing the tool list

Reconciliation deletes every tool it does not find declared in `agent.yml`, including
anything added through the Agents-tab UI. That is the point — the repo is authoritative —
but it is not recoverable from the repo, so look at the plan first.

---

## Conformance

The audit checklist for this guideline lives beside it, in [`conformance/agent.md`](conformance/agent.md) — one file, one source of truth, loaded by whoever is auditing rather than by everyone who edits a file.
