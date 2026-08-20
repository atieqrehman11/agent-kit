# TPLVAR_DISPLAY_NAME

TPLVAR_DESCRIPTION

**Type:** `agent` — an Agent Bricks **Multi-Agent Supervisor**, as config-as-code.
You supply two things: **instructions**, and a **list of tools to attach**. A
reconciler makes the live agent match them.

The **repo is authoritative**. Anything changed in the Agents-tab UI is
overwritten on the next deploy — including tools added there, which are deleted
because they are not declared here.

## Layout

```
src/managed/
├── agent.yml            the DEFINITION — display_name, description, tools
└── instructions.md      the routing instructions (sent byte-verbatim)
python/
├── deploy_agent.py      the job task entry point
├── managed.py           the reconciler
└── validate.py          checks the spec — no credentials, no network
resources/deploy.job.yml the job that IS the deploy
databricks.yml           per-environment values, passed to the job as --var
```

## Configuration

**Nothing here names an environment.** `agent.yml` references `${genie_space_id}` and friends. Those are passed as
`--var` by the deploy job, and set per target in `databricks.yml` — a Genie space
id is workspace-local, so the dev value is never valid in stg. An unresolved
`${name}` fails the deploy rather than reaching the API, and a value still left
as `TODO_SET_*` is rejected too: the API would accept it as an id and the agent
would deploy green with a tool that answers nothing.

## Verify

```bash
./run_local.sh            # validate src/managed/ — no credentials, no network
./run_local.sh plan       # what a dev deploy would add, change or DELETE
```

`validate.py` runs the same `check()` that `deploy_agent.py` runs before it touches a
workspace, so "valid" has one definition. It rejects an empty required field, no tools at
all, a duplicate `tool_id`, a tool with no `tool_type`, and a `${...}` that survived
substitution.

**`plan` is the one check `validate` cannot do.** Reconciliation deletes every live tool it
does not find declared, and that is not recoverable from the repo — so run `plan` before
any change that touches the tool list, and read the delete lines.

**Behaviour needs its own gate.** `instructions.md` and a tool `description` are the
product here, and both change routing with no compile step and no test to break. Scaffold
a suite with `{{cmd:eval:new}}`, assert **which tool answered** rather than that the reply
looked reasonable, cover an out-of-scope question and an injection attempt, and record the
pass rate in `docs/CHANGELOG.md` so the next change has a baseline to beat.

## How it deploys, and why it looks odd

A supervisor agent has **no DAB resource type**. The CI/CD controller reaches
project code only through `bundle deploy` followed by `bundle run` on a resource,
so the deploy has to *be* a resource:

```
bundle deploy  →  uploads src/ + python/ to the workspace
bundle run deploy_agent  →  runs the reconciler there, against
                            /api/2.1/supervisor-agents
```

`resources/deploy.job.yml` is that job, and `run_resources.yml` lists it — which
is what makes the controller run it. Without that entry the deploy uploads a new
spec and changes no agent, and still reports success.

dev runs the same job the controller runs, so there is one deploy path, not two.

## The two things you edit

- **`src/managed/instructions.md`** — how the supervisor should behave and route.
  For each tool, when to call it; grounding and out-of-scope rules; tone.
- **`src/managed/agent.yml: tools`** — the tools to attach. Each needs a
  `tool_id`, a `tool_type`, the type-specific reference, and a `description`.

That `description` is not documentation. It is what the supervisor reads to
decide when to route to the tool, so say what the tool does **not** cover too —
that is what stops a wrong route.

## Deployment

| Target | How |
|---|---|
| **validate** | `./run_local.sh` — offline check of the spec |
| **plan** | `./run_local.sh plan` — what a deploy would add, change or **delete** |
| **dev** | `./run_local.sh deploy` — bundle deploy, then run the job |
| **stg** | merge to the `stg` branch — the controller deploys |
| **prod** | merge to `prod`, then press play in Build → Pipelines |

Run `plan` before any change that touches the tool list. Reconciliation deletes
every tool it does not find declared, and that is not recoverable from the repo.

## Identity

The agent is found by **display_name**, not by an id, so this repo holds no
deploy state: the same commit creates the agent in a workspace that has none and
updates it in one that does. The endpoint name (`mas-<hex>-endpoint`) is assigned
by Databricks at create time and printed at the end of a deploy — any API repo
calling this agent has to be told what it is.

## Evaluation

The loop is: edit `src/managed/` → deploy → run `evaluation/` → record the
baseline in `docs/CHANGELOG.md`. Scaffold the suite with `{{cmd:eval:new}}`.
