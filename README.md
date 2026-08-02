# agent-kit

Guidelines, skills and subagents for AI coding tools, kept in one place and installed into
whichever tool you use.

`core/` is tool-agnostic — it contains no tool's paths, filenames or invocation syntax, and no
client's name. Everything tool-shaped lives in `adapters/<tool>/`. Adding a tool means adding an
adapter, never editing `core/`.

```
./install.sh                 # install into ~/.claude
./install.sh --list          # which adapters exist
./install.sh --dry-run       # validate and report; write nothing
```

---

## What's in it

**14 guidelines** — constraints that apply from context, never invoked.

| | |
|---|---|
| language / framework | `python` `python-llm` `java` `react` `streamlit` `chainlit` |
| repo type | `api` `chat-api` `pipeline` `job` `agent` `genie` |
| practice | `design` `service-structure` |

Three of them — `api`, `chat-api`, `service-structure` — ship a `<name>.conformance.md`
beside them: the audit list, split out so whoever is *writing* code loads the rules and
whoever is *auditing* loads the checklist. See [`STANDARD.md`](STANDARD.md) §1.2.

**5 skills** — procedures you deliberately run, each with scripts behind it.

| | |
|---|---|
| `/deliver:feature` | one requirement to reviewed, tested code through seven gates, then a written report |
| `/diagram:build` `/diagram:review` | draw.io diagrams, verified by rendering and reading them before they are shown |
| `/plan:release` | a release plan through nine ordered gates, scheduled and validated |
| `/scaffold:new` `:add` `:configure` `:profile` | Databricks repos by type, and their config |
| `/eval:new` | an evaluation spec in the repo that owns it |

**2 subagents** — independent workers with their own context.

`reviewer` · `qa`

---

## The three kinds, and how to choose

This is the only design decision that matters when adding something. Full rules in
[`STANDARD.md`](STANDARD.md) §1.1.

| Kind | It is | Lives in |
|---|---|---|
| **guideline** | a *constraint* — how a thing is done whenever you do it | `core/guidelines/<name>.md` |
| **skill** | a *procedure* — deliberately run, produces an artifact | `core/skills/<name>/` |
| **subagent** | an *independent worker* — own context, returns a verdict | `core/subagents/<name>.md` |

**Default to guideline. Promote to skill only if it is a procedure. Promote to subagent only
if** it reads a lot and reports a little, **or** must not see the reasoning that produced the
thing it examines, **or** runs in parallel with siblings.

A subagent costs a round trip and returns a summary instead of the reasoning. Paying that for
something that could have been text in your current context is pure loss.

---

## Adding a skill

```
core/skills/<name>/
  SKILL.md            REQUIRED  frontmatter + body; the model-invoked entry point
  commands/<verb>.md  optional  user-invoked entry points → /<name>:<verb>
  README.md           optional  documentation for maintainers; never installed
  reference/**        payload   long-form material the skill reads
  templates/**        payload   files the skill copies or renders
  *.py                payload   scripts the skill runs
```

1. Write `SKILL.md` with `name`, `kind`, and a `description` that says **when to reach for it**.
   The description is the only signal a model has when choosing between artifacts.
2. **Only `SKILL.md` and `commands/*.md` are registered.** Everything else is payload. If you
   are unsure whether a file is an entry point, it is not.
3. Address your own files with `__SKILL_DIR__`, shared user state with `__KIT_DATA_DIR__`, and
   other commands with `{{cmd:<skill>:<verb>}}`. Never a hardcoded path, a `~`-relative path, or
   one tool's slash syntax.
4. Run the installer. Its verify step will tell you what you got wrong — an unresolvable
   `{{cmd:…}}` or invalid frontmatter fails the install before anything is written.

---

## Adding an adapter

An adapter installs `core/` into one tool. It owns paths, file formats, registration mechanics,
hooks and settings — everything tool-shaped.

1. Read [`STANDARD.md`](STANDARD.md) Part 2. It lists eleven obligations and the conformance
   checklist you will be held to.
2. Copy the shape of [`adapters/claude/install.py`](adapters/claude/install.py) — the reference
   implementation. Every obligation is annotated there.
3. **You may support a subset.** If your tool has no native form for a kind, render what you can
   and *log by name* what you skipped. Silently dropping a kind is a contract violation. This
   clause is what lets a new adapter ship without changing `core/`.
4. Resolve the markers: `__SKILL_DIR__`, `__KIT_DATA_DIR__`, `__GUIDELINES_DIR__`, `{{cmd:…}}`,
   `{{args}}`. A surviving marker is a failed install, not a warning.
5. Provide a kit data dir and **never overwrite it** — user-filled state lives there precisely
   because skill directories are replaced wholesale on every install.

`adapters/codex/` is parked: it holds pre-existing material and has no installer yet.

---

## Layout

```
core/            tool-agnostic — the actual content
  guidelines/    skills/    subagents/
adapters/
  claude/        install.py · hooks/ — the reference implementation
  codex/         parked; see its README
STANDARD.md      the artifact format, and the adapter contract
install.sh       dispatcher: --target <tool>
```

Edit the repo and re-run the installer. Anything hand-edited inside an installed copy is
replaced on the next install.
