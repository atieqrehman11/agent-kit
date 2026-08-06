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

## 1.2 Guideline layout

```
core/guidelines/<name>.md                    REQUIRED   frontmatter + body. The rules, and why.
core/guidelines/conformance/<name>.md        optional   PAYLOAD — the checklist someone walks
                                                        to audit a change. Never registered.
```

**The split exists because a guideline has two readers with opposite needs.** Someone
*writing* code needs the rules and the reasoning; someone *reviewing* it needs a list of
checks. One file serves both by making each load the other's half.

**Why a subdirectory rather than a `<name>.conformance.md` sibling.** The sheets carry no
frontmatter, so under a flat layout the *only* thing separating payload from artifact was a
filename suffix, and discovery had to test for it — miss the test and
`service-structure.conformance.md` derives the artifact name
`service-structure.conformance`, matches no frontmatter, and fails obligation 2. A
subdirectory makes that unrepresentable: discovery enumerates depth-1 `*.md`, and a directory
is not one. Same reasoning as §1.4's allowlist — structure the rule so the failure cannot be
expressed, rather than string-matching for it.

The cost is that a sheet and its guideline now share a filename, distinguished only by
directory. That is deliberate: it is what makes the pairing exact and the orphan check a
plain set comparison.

Measured on this repo before the split: a single edit to an API router loaded `python`,
`api` and `service-structure` — about 5,650 tokens, of which **884 were conformance
checkboxes the implementer never reads**. The reviewer paid the mirror of that bill, loading
4,000 tokens of teaching prose to reach 23 checkboxes. Neither reader was served by the
coupling; both paid for it.

Rules:

- The sheet is **payload**: installed under `guidelines/conformance/`, never registered, never
  invocable. It has **no frontmatter** — it is not an entry point, and §1.5 does not apply.
- `<name>` must match a guideline that exists. A sheet naming no guideline is a failed
  install, the same class of error as a dangling `{{cmd:…}}`.
- **The installed tree mirrors `core/`.** The path a reviewer is told to read is the path a
  maintainer edits; an adapter that flattens or relocates the directory breaks every
  cross-reference written into the sheets.
- **The checklist lives in the sheet and nowhere else.** A guideline that both ships a sheet
  and keeps its own checklist has two sources of truth, which is the condition this split
  exists to remove.
- **Every check must be defined in the guideline.** A sheet states rules in binary form; it
  never introduces one. A check with no rule behind it makes the sheet the source of truth,
  and then whoever is writing the code has no way to learn the rule exists.
- Add one only where a reviewer genuinely walks a checklist independently of the prose. An
  "acceptance criteria check" that tells the *implementer* to tick their own criteria is part
  of the guideline body — it has one reader, so splitting it buys nothing and costs a file.

Anything that needs to audit a change reads the sheet directly, by path, via
`__GUIDELINES_DIR__` (§1.6) — it does not load the guideline to get at it.

## 1.3 Skill layout

```
core/skills/<name>/
  SKILL.md               REQUIRED   frontmatter + body. The model-invoked entry point.
  commands/<verb>.md     optional   user-invoked entry points → /<name>:<verb>. Frontmatter
                                    too — an entry point without a description is §1.5's
                                    failure, whoever invokes it.
  README.md              optional   DOCUMENTATION — for whoever maintains the skill.
                                    Never registered, never installed. Lives here so it
                                    cannot drift away from what it documents.
  docs/**                optional   DOCUMENTATION — diagrams and long-form notes ABOUT
                                    the skill. Same rule as README.md, same reason.
  reference/**           optional   PAYLOAD — long-form material the skill reads
  templates/**           optional   PAYLOAD — files the skill copies or renders
  *.py                   optional   PAYLOAD — scripts the skill runs
```

**`docs/` and `reference/` look alike and are opposites.** The test is *who reads it*:
`reference/` is read **by the skill, at run time** — it is payload, and it installs.
`docs/` is read **by a human, deciding whether to change the skill** — it never installs,
so a workflow diagram does not ship a PNG into every user's install.

Anything documenting **the kit as a whole** rather than one skill belongs in the repo's
top-level `docs/`, not here. The split is by subject: a diagram of the scaffold workflow
sits with the scaffold skill and cannot drift from it; a diagram of how artifacts reach an
installed tree belongs to no single skill.

## 1.4 The entry-point rule

**An adapter registers exactly two things and nothing else:**

```
core/skills/<name>/SKILL.md          → one model-invoked entry
core/skills/<name>/commands/*.md     → one user-invoked entry each  (depth 1 only)
```

**Everything else is payload or documentation.** Payload is read, copied, executed or rendered
*by* a skill; `README.md` and `docs/**` document the skill for its maintainers. Neither is ever
invocable, at any depth, and an adapter installs payload but not documentation.

`core/guidelines/conformance/<name>.md` (§1.2) is payload too, and the same sentence covers it:
installed, never registered. A guideline is registered from a **depth-1** `<name>.md` alone, so
nothing inside `conformance/` can become a phantom entry point.

This is an **allowlist, and that is the point.** The predecessor to this standard used a
denylist — "register every `.md`, except the `README.md` at the skill root" — and a denylist
fails open. Every file the rule failed to anticipate became a command. At the time this standard
was written the live install registered **40 commands, of which 22 were payload**: template
`CHANGELOG`s, a Databricks job `README`, and the reference material for the diagram and planning
skills. Adding one skill added two more phantoms. An allowlist cannot fail that way.

A phantom entry point is not cosmetic. Every registered command spends context in the model's
selection list, and a model that can invoke `scaffold:templates:genie:genie-space:CHANGELOG`
will eventually try to.

## 1.5 Frontmatter

Required on **every entry point**, of every kind — including each `commands/<verb>.md`.

```yaml
---
name: diagram                 # kebab-case; MUST match the directory or file name
kind: skill                   # guideline | skill | subagent | command
description: >                # prose, 1–2 sentences, stating WHEN to reach for this.
  Build a draw.io diagram and verify it renders before presenting it.
  Use for architecture, network, data-flow, auth diagrams and ERDs.
---
```

`kind: command` is the one kind that is not a top-level artifact — it belongs to the skill whose
`commands/` directory holds it, and its `name` is the verb, matching the filename. It is listed
here because §1.4 registers it as an entry point, and **the rules for an entry point do not
depend on whether a model or a user is the one selecting it.** A command's description is what a
user reads in a command picker, at exactly the moment they are choosing between commands — the
same job the description does for a model. Omitting it does not degrade selection quietly; it
leaves the line blank.

> Measured, after Part 1 was first written: all eight commands in `core/` carried no frontmatter
> at all. The adapter validated `description` for three kinds and copied command files through
> byte-for-byte, because §1.5 said "every artifact" and a command had not been named as one. The
> `/` picker listed eight commands with nothing beside them.

Optional:

```yaml
version: 1.0
arguments: "[path or branch; default = current diff]"   # hint for entry points that take input
requires:
  bin: [drawio]               # adapter warns, never blocks, when missing
  python: [openpyxl]
applies_to:                   # guidelines only — file patterns that should trigger loading
  - "**/*.py"
```

**Every guideline must state when it applies** — as `applies_to` globs, or in the description,
or both. Prefer globs where a file pattern genuinely signals the context. Leave them off where
one does not: a wrong glob is worse than none, because it fires constantly and gets tuned out.
`design` has no file signal (it is triggered by an activity), and `python-llm` deliberately
avoids `**/*.py` because it would fire on every Python file alongside `python`.

**How an adapter uses it: append it to the rendered description — do not build a hook.** The
model then reads the trigger at the moment it is choosing what to load. A hook that injects a
guideline on every matching edit fires whether you are fixing a typo or designing a pipeline,
and a rule that repeats on every keystroke stops being read.

`arguments` is a **description**, not a schema. Each adapter maps it onto whatever its tool
uses to advertise arguments; an adapter with no such concept ignores it.

**`description` must be prose, and must say when to use the thing.** It is the only signal a
model has when choosing between artifacts. Nine personas in the predecessor set had a body
consisting of a single `@`-import line, so the description the model saw was a filesystem path —
which is why nothing could sensibly choose between `architect` and `decomposer`.

`name` matching the directory is what lets an adapter replace one artifact without a manifest.

## 1.6 Path tokens

An artifact's files move to an install location it cannot know in advance. Two tokens are
resolved at install time. They exist separately because they have **opposite lifecycles**.

| Token | Resolves to | Lifecycle |
|---|---|---|
| `__SKILL_DIR__` | the absolute path of *this artifact's* installed directory | **replaced wholesale on every install** (obligation 6) |
| `__KIT_DATA_DIR__` | one directory per install, shared by every artifact | **never created over, never deleted** by an install |
| `__GUIDELINES_DIR__` | where `core/guidelines/` was installed | replaced with the rest of `core/` |
| `__PROJECT_SCOPE_DIR__` | the directory *name* marking a project scope for per-project user state | a naming convention, not a path — see below |
| `__ORG_PREFIX__` | `"<Org> "`, or the empty string when no org is configured | read from user data at install time |

`__ORG_PREFIX__` is not a path — it is a **value** token, and it is listed here because
leaving it undocumented is what let it ship. Six guidelines open with
`# Python Standards — __ORG_PREFIX__shared standard`. The scaffold resolved it when copying a
guideline into a generated repo; the adapter that installs the same file did not, because it
had never been told the token existed. Every installed guideline carried the literal
`__ORG_PREFIX__` in its H1 while verification reported "no unresolved markers".

**This is why the verify in §2.4 must be a general scan and not a list.** The check enumerated
three token names, so a fourth was invisible to it — the same way a denylist of entry points
made 22 payload files invocable (§1.4). An adapter MUST verify by searching for *any*
surviving `__[A-Z][A-Z0-9_]*__`, not by checking off the tokens in this table. The table tells
you what to resolve; it must not be the thing you validate against.

`__GUIDELINES_DIR__` exists because a skill sometimes needs a guideline as a *file*, not as
context — `scaffold` writes the relevant standards into every repo it generates. Without it
the skill keeps its own copy, which is how this repo came to hold two byte-identical copies
of the API standards, 395 lines each, in two different folders.

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

### Why one data dir is not one profile

The data dir is per **install**. Some of the state inside it is not — it is per **client**,
or per codebase. The scaffold profile is the clear case: `org`, `team_name`, the CI
controller, the cluster policies. Those are precisely the values that differ between the
clients one machine serves, and the profile is read by a script whose job is to bake them
permanently into a generated repo.

With one profile per install, standing in client B's tree and scaffolding produces a repo
branded for client A, wired to client A's CI controller — and nothing says so, because a
generated repo looks correct either way. The failure surfaces at review, or at deploy.

So user state that can be client-specific is **scoped**, and a scope is a directory:

```
$AGENT_KIT_PROFILE                       an explicit file, for one invocation
<dir>/__PROJECT_SCOPE_DIR__/<name>      nearest project scope, walking up from the cwd
<kit data dir>/<name>                   install-wide fallback
```

`__PROJECT_SCOPE_DIR__` is a token for the same reason `__KIT_DATA_DIR__` is: **what a
tool calls its per-project directory is the adapter's business.** Writing the Claude
adapter's `.claude` into a `core/` script is the leak §2.5 tests for, and hardcoding it
would silently do nothing under any other tool. Unresolved — a checkout running with no
adapter — it means *there is no project convention here*, so the walk is skipped
entirely rather than guessed at. `$AGENT_KIT_PROJECT_DIR` is the escape hatch.

Three obligations follow, and they are what make the scoping worth having:

- **The walk skips the data dir itself.** An install into `~/.claude` would otherwise
  report itself as the project scope for everything under `$HOME`.
- **Every consumer states what it resolved.** Not on request — on every run, next to the
  work it is about to do. Silent resolution is the defect; resolving to the wrong file is
  only its symptom. A consumer that finds no scope profile while standing inside a project
  that *has* a `.claude/` says so too, because that is the case that produces the wrongly
  branded repo.
- **Writing and reading agree.** The command that writes a scoped profile resolves the
  scope by the same walk as the commands that read it, including before the first value is
  applied — otherwise "fill in the sheet, then apply it" writes to a different scope than
  the one the sheet was generated for.

What stays install-wide: anything resolved at **install time** rather than run time.
`__ORG_PREFIX__` is baked into installed guidelines once per install (§1.6), so it reads
the install-wide profile and a per-client value cannot reach it. An adapter that wants
per-client guideline branding installs per client.

## 1.6.1 Command references

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

## 1.7 What may not appear in `core/`

`core/` is tool-agnostic and client-agnostic. It must not contain:

- **Tool-specific paths, filenames or syntax** — `~/.claude`, `CLAUDE.md`, `AGENTS.md`, any
  adapter's directory layout, or a literal `/skill:verb` invocation. Use `{{cmd:…}}` (§1.6.1).
- **The name of any agent tool** — in prose, in comments, in generated templates. Naming an
  LLM *provider* or model is fine: that is what the code integrates with, not what runs it.
- **A tool's frontmatter keys or argument variables** — use `arguments:` (§1.5) and `{{args}}`
  (§1.6.1), which adapters map onto their own.
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
| 1 | **Discover** | Enumerate `core/guidelines`, `core/skills`, `core/subagents`. Read frontmatter. Derive everything from the tree — never from a hardcoded list of names. Everything under `core/guidelines/conformance/` is payload of the guideline it names, not an artifact of its own (§1.2). |
| 2 | **Validate before writing** | Reject missing or malformed frontmatter, a `name` that disagrees with its path, or a `description` that is not prose. Fail before the first byte is written, so a bad artifact cannot half-install. |
| 3 | **Render by kind** | Map each kind onto the tool's native form (§2.2). |
| 4 | **Register only entry points** | `SKILL.md` and `commands/*.md` at depth 1. Payload is copied, never registered — including every `conformance/<name>.md`. |
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
- [ ] Every `conformance/<name>.md` was installed, and none was registered as an entry point
- [ ] Every `conformance/<name>.md` names a guideline that exists — a sheet with no guideline fails the install
- [ ] Zero surviving markers — scanned as **any** `__[A-Z][A-Z0-9_]*__`, `{{cmd:…}}` or `{{args}}`, never as a list of known names (§1.6)
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

### Build the verification in the same pass as the installer

**An adapter and its conformance run ship together, or neither ships.** Not a process
preference — the reference adapter shipped 11 of its 13 checks green while missing
obligation 10 (uninstall) *entirely*, because nothing had ever tried to uninstall. An
unverified adapter looks finished and is not.

A second adapter is also the first place a tool-specific assumption can quietly re-enter
`core/`, since nothing but a conformance run exercises the §2.2 subset clause. Write the
checks against **this document**, not against the tool — that is what lets most of them run
unchanged against the next adapter, and `adapters/claude/conformance.sh` is written that way
deliberately.

**Defer the whole thing rather than half of it.** Writing an installer against a contract
nobody has exercised produces a guess. It is cheaper to have no adapter than one that reports
success it has not earned.

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
