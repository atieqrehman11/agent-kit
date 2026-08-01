# agent-kit — The Standard

What this repo contains, how it is shaped, and what any tool adapter must do with it.

Two parts:

- **Part 1 — the artifact format.** What a guideline, a skill and a subagent are, how each is
  laid out, and which files are invocable. Tool-agnostic; nothing here names a vendor.
- **Part 2 — the adapter contract.** What a program must do to install this repo into a
  specific tool, and the checklist it is held to.

`adapters/claude/` is the reference implementation of Part 2. It is not privileged: anything it
needs that is not written down here is a bug in this document.

---

# Part 1 — The artifact format

## 1.1 Three kinds

Everything in `core/` is exactly one of three kinds, declared in its frontmatter.

| Kind | It is… | Invoked by | Lives in |
|---|---|---|---|
| **guideline** | A *constraint* — how a thing should be done whenever you do it | nobody; it applies from context | `core/guidelines/<name>.md` |
| **skill** | A *procedure* — deliberately run, produces an artifact or a decision | the user, by name | `core/skills/<name>/` |
| **subagent** | An *independent worker* — its own context, returns a verdict | an orchestrator or the model | `core/subagents/<name>.md` |

### The promotion test

**Default to guideline. Promote to skill only if it is a procedure. Promote to subagent only if
at least one of these holds:**

1. **Context economy** — it reads a lot and reports a little.
2. **Independence** — it must *not* see the reasoning that produced the thing it examines.
3. **Fan-out** — several instances run at once over different inputs.

A capability that fails all three is a skill. A skill nobody deliberately invokes is a guideline.

> Why this is a rule and not a preference: a subagent costs a round trip and returns a summary
> instead of the reasoning. Paying that for something that could have been text in your current
> context is pure loss. Reviewers and QA earn it — a reviewer that watched the code being written
> is anchored to it, and independence is the entire product. A Python style guide does not.

**Do not register one capability as two kinds.** One artifact, one kind, one registration.

## 1.2 Skill layout

```
core/skills/<name>/
  SKILL.md               REQUIRED   frontmatter + body. The model-invoked entry point.
  commands/<verb>.md     optional   user-invoked entry points → /<name>:<verb>
  reference/**           optional   PAYLOAD — long-form material the skill reads
  templates/**           optional   PAYLOAD — files the skill copies or renders
  *.py                   optional   PAYLOAD — scripts the skill runs
```

## 1.3 The entry-point rule

**An adapter registers exactly two things and nothing else:**

```
core/skills/<name>/SKILL.md          → one model-invoked entry
core/skills/<name>/commands/*.md     → one user-invoked entry each  (depth 1 only)
```

**Everything else is payload.** Payload is read, copied, executed or rendered *by* a skill. It is
never itself invocable, at any depth.

This is an **allowlist, and that is the point.** The predecessor to this standard used a
denylist — "register every `.md`, except the `README.md` at the skill root" — and a denylist
fails open. Every file the rule failed to anticipate became a command. At the time this standard
was written the live install registered **40 commands, of which 22 were payload**: template
`CHANGELOG`s, a Databricks job `README`, and the reference material for the diagram and planning
skills. Adding one skill added two more phantoms. An allowlist cannot fail that way.

A phantom entry point is not cosmetic. Every registered command spends context in the model's
selection list, and a model that can invoke `scaffold:templates:genie:genie-space:CHANGELOG`
will eventually try to.

## 1.4 Frontmatter

Required on every artifact of every kind.

```yaml
---
name: diagram                 # kebab-case; MUST match the directory or file name
kind: skill                   # guideline | skill | subagent
description: >                # prose, 1–2 sentences, stating WHEN to reach for this.
  Build a draw.io diagram and verify it renders before presenting it.
  Use for architecture, network, data-flow, auth diagrams and ERDs.
---
```

Optional:

```yaml
version: 1.0
arguments: "[path or branch; default = current diff]"   # hint for entry points that take input
requires:
  bin: [drawio]               # adapter warns, never blocks, when missing
  python: [openpyxl]
applies_to:                   # guidelines only — the context that should trigger loading
  - "**/*.py"
```

`arguments` is a **description**, not a schema. Each adapter maps it onto whatever its tool
uses to advertise arguments; an adapter with no such concept ignores it.

**`description` must be prose, and must say when to use the thing.** It is the only signal a
model has when choosing between artifacts. Nine personas in the predecessor set had a body
consisting of a single `@`-import line, so the description the model saw was a filesystem path —
which is why nothing could sensibly choose between `architect` and `decomposer`.

`name` matching the directory is what lets an adapter replace one artifact without a manifest.

## 1.5 Path tokens

An artifact's files move to an install location it cannot know in advance. Two tokens are
resolved at install time. They exist separately because they have **opposite lifecycles**.

| Token | Resolves to | Lifecycle |
|---|---|---|
| `__SKILL_DIR__` | the absolute path of *this artifact's* installed directory | **replaced wholesale on every install** (obligation 6) |
| `__KIT_DATA_DIR__` | one directory per install, shared by every artifact | **never created over, never deleted** by an install |

- Any text file in an artifact MAY contain either token.
- An install with any surviving token is a **failed install**, not a warning.

Artifacts MUST NOT hardcode absolute paths, `~`, or paths relative to the current working
directory, and MUST NOT infer either location from their own position on disk.

### Why `__KIT_DATA_DIR__` is not just "somewhere near the skill dir"

User state must outlive an install. A filled-in profile sheet, a saved configuration — these
are written by the user and read by *several* skills, and obligation 6 would destroy them if
they lived inside a skill directory.

The predecessor code understood the requirement and expressed it as
`os.path.dirname(os.path.dirname(__file__))` — "two levels up from wherever I was installed."
That is a script inferring the installer's directory layout. It held only while one adapter
used one layout, it broke silently for any other, and a second script gave up entirely and
hardcoded `~/.claude/spec-profile.json`. A shared resource with no sanctioned home is a
resource every script will invent a different guess for.

Resolution order for a script that needs it:

```
$AGENT_KIT_DATA_DIR          escape hatch, and how a repo checkout runs uninstalled
__KIT_DATA_DIR__             baked in at install time
repo root                    dev fallback: walk up to the directory holding STANDARD.md
```

## 1.5.1 Command references

Artifacts constantly need to name each other — in help text, in error messages, in prose
("run the review command on it first"). Writing that as one tool's invocation syntax couples
`core/` to that tool.

```
Write this                     Claude renders          another adapter renders
{{cmd:diagram:review}}         /diagram:review         whatever it uses
{{cmd:scaffold}}               /scaffold               ...
```

- `{{cmd:<skill>:<verb>}}` refers to a `commands/<verb>.md` entry point.
- `{{cmd:<skill>}}` refers to the skill itself, via its `SKILL.md`.
- `{{args}}` is whatever the caller passed to this entry point. Every tool has some way to
  hand an invocation its arguments; none of them spell it the same, so artifacts must not
  spell it at all.
- The adapter renders both in its own syntax at install time.
- **The reference must resolve.** An adapter MUST fail on a `{{cmd:…}}` naming a skill or
  verb that does not exist — this is a broken link in user-facing text, and it is exactly
  the class of bug that mechanical checking is for.

> This rule paid for itself the day it was written. Tokenising 87 references surfaced eight
> that pointed at nothing: five told the user to run `/usecase-eval:new`, a name the eval
> skill has never had, and three referred to `spec` verbs that were never implemented. All
> eight had been shipping as instructions to the user.

## 1.6 What may not appear in `core/`

`core/` is tool-agnostic and client-agnostic. It must not contain:

- **Tool-specific paths, filenames or syntax** — `~/.claude`, `CLAUDE.md`, `AGENTS.md`, any
  adapter's directory layout, or a literal `/skill:verb` invocation. Use `{{cmd:…}}` (§1.5.1).
- **The name of any agent tool** — in prose, in comments, in generated templates. Naming an
  LLM *provider* or model is fine: that is what the code integrates with, not what runs it.
- **A tool's frontmatter keys or argument variables** — use `arguments:` (§1.4) and `{{args}}`
  (§1.5.1), which adapters map onto their own.
- **Client names.** No client, engagement or customer appears in `core/`. Client-specific
  material belongs in that client's own project configuration, not here.
- **Secrets, tokens, hostnames, internal URLs, policy IDs, or personal paths.** Installed-time
  values come from the profile sheet, which is generated per-install and never committed.

These are mechanically checkable, and Part 2 requires an adapter's verify step to check them.

---

# Part 2 — The adapter contract

An adapter installs `core/` into one tool. It lives in `adapters/<tool>/` and owns everything
tool-shaped: paths, file formats, registration mechanics, hooks, settings fragments.

## 2.1 Obligations

An adapter MUST:

| # | Obligation | Detail |
|---|---|---|
| 1 | **Discover** | Enumerate `core/guidelines`, `core/skills`, `core/subagents`. Read frontmatter. Derive everything from the tree — never from a hardcoded list of names. |
| 2 | **Validate before writing** | Reject missing or malformed frontmatter, a `name` that disagrees with its path, or a `description` that is not prose. Fail before the first byte is written, so a bad artifact cannot half-install. |
| 3 | **Render by kind** | Map each kind onto the tool's native form (§2.2). |
| 4 | **Register only entry points** | `SKILL.md` and `commands/*.md` at depth 1. Payload is copied, never registered. |
| 5 | **Resolve tokens and command references** | Rewrite every `__SKILL_DIR__`, `__KIT_DATA_DIR__` and `{{cmd:…}}`; verify zero remain. A `{{cmd:…}}` naming a skill or verb that does not exist is a **failed install**, not a warning. |
| 6 | **Replace, do not merge** | Per artifact: remove the installed copy, then write. A file deleted from `core/` must not linger as a stale command. |
| 7 | **Preserve user data** | Never overwrite anything the user filled in — the profile sheet above all. Offer a flag to skip regeneration and default to preserving. |
| 8 | **Verify** | §2.4. Report failures; do not exit 0 on a broken install. |
| 9 | **Write a receipt** | Source path, source version, timestamp, and every artifact installed. |
| 10 | **Uninstall** | Remove exactly what the receipt lists, and nothing else. Never the kit data dir. |
| 11 | **Provide a kit data dir** | Choose one directory per install for shared user state, create it if absent, and resolve `__KIT_DATA_DIR__` to it. It is **exempt from obligation 6** — an install never replaces, clears or reinitialises it. Where it goes is the adapter's choice; that it exists is not. |

An adapter MUST NOT write outside its declared install root, and MUST NOT modify `core/`.

## 2.2 Subset rendering — the clause that makes a second adapter possible

A tool may have no native form for a kind. **An adapter MAY render a subset of the three kinds,
and MAY render a kind in a degraded form** — provided it:

- states in its README which kinds it supports and how each is expressed, and
- **logs every artifact it skipped, by name**, at install time.

Silently dropping a kind is a contract violation. A user who cannot see what was skipped will
assume coverage that does not exist.

This clause exists so that adding a tool never requires changing `core/`. If a new adapter cannot
express something, that is a fact about the tool, recorded at install time — not a reason to
reshape the standard.

### Reference mapping — `adapters/claude/`

| Kind | Rendered to | User-invocable | Model-invocable |
|---|---|---|---|
| guideline | `~/.claude/skills/<name>/SKILL.md`, description shaped as a trigger | no | yes, from context |
| skill | `~/.claude/skills/<name>/SKILL.md` **+** `~/.claude/commands/<name>/<verb>.md` | yes, `/<name>:<verb>` | yes |
| subagent | `~/.claude/agents/<name>.md` with `name` + `description` frontmatter | via the Agent tool | yes |

Note the guideline row: it is rendered model-invocable but **not** user-invocable, deliberately.
A Python standard that only applies when someone remembers to type `/python-dev` does not apply.

## 2.3 Preflight

Check `requires` before installing. A missing dependency is a **warning naming the artifact that
needs it and the command that installs it** — never a block. Most of the kit works without
`drawio` or `openpyxl`; refusing to install everything because one skill lacks a renderer is the
wrong trade.

## 2.4 Verification — run every install, all binary

- [ ] Every artifact has valid frontmatter; every `name` matches its path
- [ ] Every `description` is prose, not a path or a filename
- [ ] **Registered entry-point count equals declared entry-point count** — zero payload registered
- [ ] Zero surviving `__SKILL_DIR__`, `__KIT_DATA_DIR__`, `{{cmd:…}}` or `{{args}}` markers
- [ ] Every `{{cmd:…}}` resolved to a skill and verb that exist
- [ ] The kit data dir exists, and its contents are byte-identical to before the install
- [ ] Every installed script parses
- [ ] Every skipped artifact was logged by name
- [ ] User-filled data is byte-identical to before the install
- [ ] A receipt was written and lists every installed artifact

## 2.5 Conformance — a new adapter is held to this

- [ ] Obligations 1–10 implemented
- [ ] README states which kinds are supported and how each is expressed
- [ ] Skipped artifacts logged by name
- [ ] §2.4 verification runs on every install and fails loudly
- [ ] Uninstall removes exactly the receipt contents
- [ ] **Leak test:** no file under `core/` references this tool's paths, filenames or invocation
      syntax. If the adapter needed such a reference, the standard is wrong — fix it here, not
      by special-casing `core/`.
- [ ] Installing twice in a row produces an identical tree
- [ ] Installing after deleting an artifact from `core/` removes it from the install

---

## Appendix — how to add a skill

1. `mkdir core/skills/<name>` and write `SKILL.md` with `name`, `kind: skill`, and a
   `description` that says *when to reach for it*.
2. Apply the promotion test (§1.1). If it is not a procedure someone deliberately runs, it is a
   guideline — put it in `core/guidelines/` instead.
3. Put user-invocable entry points in `commands/<verb>.md`. Put everything else in `reference/`,
   `templates/`, or scripts. **If you are unsure whether a file is an entry point, it is not.**
4. Address your own files with `__SKILL_DIR__`, and anything the user fills in or that another
   skill also reads with `__KIT_DATA_DIR__`. Never a hardcoded path, a `~`-relative path, or a
   guess derived from your own position on disk.
5. Run the adapter install. §2.4 will tell you what you got wrong.
