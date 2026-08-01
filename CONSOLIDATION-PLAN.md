# Agent Config Consolidation — Plan

Define a tool-agnostic **standard** for guidelines, personas and skills; merge `ai-clone` +
`claude-skills` into one versioned repo built to that standard; ship **Claude as the first
and only adapter**; re-tier the four `.claude` directories so nothing is duplicated.

Codex is deliberately out of scope for this pass — see **Deferred**. The adapter *contract*
is written now so adding Codex later is an adapter, not a refactor.

**Status:** Gates 1–6 complete. Gates 7–8 (resource-constrained schedule, Gantt) are
deliberately **not** run — one person, ~13 days; a levelling model over a single seat adds
nothing a dependency-ordered list does not already carry. Phase exit gates are kept.

**Estimates are human hands-on-keyboard man-days**, comparable with client plans. If Claude
executes it, most of Phases 3 and 5 collapses to minutes; Phase 2 and Phase 4 do not.

---

## Sequencing decision — fix first, or enhance first?

**Do Phase 0 and Phase 1 first (1.5 d). Skip the rest of the fix list.**

| Fix from the review | Do now? | Why |
|---|---|---|
| Commit untracked `claude-skills/commands/plan/` | **Yes** | Never committed. One `rm -rf` from gone. |
| `git init` ai-clone | **Yes** | Entire repo untracked. Same exposure. |
| Back up all four `.claude` trees | **Yes** | Everything after this edits them. |
| Break the `~/.claude/commands` symlink, reinstall | **Yes** | Not double work — it *is* migration step one. You cannot cleanly split the two repos while the installer writes through a symlink into one of them. Side benefit: `/plan:release` works and `/scaffold:new` stops being 143 lines stale, days before the rest lands. |
| Collapse the 4 duplicate pairs | **No** | This is M-05, and the winner depends on the standard. |
| Re-tier CLAUDE.md and settings | **No** | Phase 5. Depends on where guidelines land. |
| Fix the dead/misfiled skills | **No** | A-05. Depends on the format defined in S-01. |

**Why the standard comes before the merge.** Writing S-01 first means M-01…M-04 move files
*into their final shape*. Merging first would mean moving every file, then rewriting every
file — the conformance pass alone would cost ~1.5 d instead of the 0.5 d verification it is
now.

---

## Decisions (open)

| ID | Decision | Options | Recommendation | Owner |
|---|---|---|---|---|
| D-01 | Name for the merged repo | `agent-kit` · `ai-workbench` · `dev-standards` | **Decided — `agent-kit`** | Decided |
| D-02 | Shared with Confiz teammates / published? | private · Confiz-internal · **local-only** | **Decided — local-only.** No pushes. `origin` (`atieqrehman11/claude-skills`, PUBLIC) stays at `a8df482` and is now stale; agent-kit is a local repo. Keep `core/` client-free anyway — M-06 and the Phase 3 grep gate enforce it, and it keeps a future push cheap | Decided |
| D-03 | Does `claude-skills` git history survive? | keep · fresh | **Keep**, but low stakes — only 3 commits exist; `git mv` preserves them at zero cost. Do not let this block anything | You |
| D-04 | Skill granularity, and what counts as invocable | single · namespace · **both** | **Decided — both**, and entry points are an **allowlist** (`SKILL.md` + `commands/*.md` depth 1). See `STANDARD.md` §1.3 | Decided |
| D-06 | One reviewer, or one per aspect (api / etl / agent / genie)? | one · per-aspect · **one + guidelines** | **Decided — one.** Only the standards vary by aspect; ~80% of a reviewer is invariant. `reviewer` takes the guidelines as its contract | Decided |
| D-07 | Are the `*_STANDARDS.md` templates or guidelines? | templates · **guidelines** | **Decided — guidelines.** A standard applies whether or not this tool scaffolded the repo. Filing them as templates is what let `api` acquire a second copy | Decided |
| D-08 | How does a guideline get loaded — description or hook? | **description** · hook | **Decided — description.** The adapter appends `applies_to` to the rendered description. A hook firing on every matching edit becomes noise and gets tuned out | Decided |
| D-05 | Are the 9 personas skills, subagents, or something else? | all skills · all subagents · **three kinds** | **Decided — three kinds**: 5 guidelines, 2 skills, 2 subagents. Promotion test in `STANDARD.md` §1.1 | Decided |

### On D-01

Both current names point at the wrong thing: `ai-clone` names *you*, `claude-skills` names
*one vendor* — and the point of the restructure is that the core outlives any one tool.

- **`agent-kit`** *(recommended)* — tool-neutral; "kit" honestly covers guidelines + personas
  + skills + installers. Short, which matters: the absolute path is baked into hundreds of
  installed files via `__SKILL_DIR__`.
- `ai-workbench` — better if you later add tooling beyond agent configuration.
- `dev-standards` — better if D-02 lands on "hand this to teammates"; foregrounds the
  guidelines rather than the automation.

**Constraint:** renaming later forces a full reinstall. Pick once. Below, `$KIT` is the chosen
name at `~/$KIT`.

### On D-04 — the one design decision the standard turns on

**Measured defect that decides this.** The current model is "every `.md` under a skill
directory is a slash command." Of the 26 `.md` files that registers today, **6 are real entry
points and 20 are payload** — `reference/` and `templates/` files that became invocable by
accident. `scaffold:templates:genie:genie-space:CHANGELOG` and a Databricks job README template
are, right now, commands the model can select. `install.sh` strips the root `README.md` for
exactly this reason but never walks deeper. **77% of the command namespace is data.**

Separately, the nine persona commands carry no description: the whole file body is an
`@`-import line, so what the model sees when choosing between `/architect` and `/decomposer`
is the string `@/Users/atieqrehman/ai-clone/agents/architect.md`.

**Recommendation — three rules, in order of importance:**

1. **Payload is not an entry point.** Only files in a declared location register as invocable.
   `reference/` and `templates/` are data the skill *reads*, never callable. Removes 20 phantom
   commands. This is the load-bearing rule — 2 and 3 improve selection quality, 1 fixes
   something actively wrong.
2. **One capability = one folder, emitting both forms.** A `SKILL.md` (when the model should
   reach for it) plus zero or more command entry points (what the user types). Keeps the
   `/scaffold:new` UX and adds auto-trigger. An adapter renders whichever forms its tool
   supports — the same subset clause that makes a second adapter possible, which is why it
   belongs in the standard now, while there is one adapter to test it against.
3. **Every entry point carries a real description.** Frontmatter `description` is mandatory and
   must be prose, not a path. Nine personas fail this today.

### On D-05 — guideline vs skill vs subagent

**Measured state.** None of the nine `ai-clone/agents/*.md` files carry YAML frontmatter, so
the `~/.claude/agents` symlink registers **zero subagents** — confirmed against a live session's
agent list. They function only as slash commands. Yet their *content* is written as subagent
contracts: every one has an `## Input protocol`, and `python-dev.md` ends with
`## Verdict line (for orchestrator parsing — mandatory first line)`. They were built for a
hand-rolled orchestrator that was never written. **Written as agents, installed as skills.**

**The standard must name three kinds, not two:**

| Kind | Test | Which personas |
|---|---|---|
| **Guideline** | A *constraint* that applies whenever you touch the thing — never invoked | `python-dev` `java-dev` `react-dev` `chainlit-dev` `streamlit-dev` |
| **Skill** | A *procedure* deliberately run in the current context | `architect` `decomposer` |
| **Subagent** | Needs its own context budget or genuine independence | `reviewer` `qa` |

**Promotion test — default to skill; promote to subagent only if one holds:** it reads a lot and
reports a little · it must *not* see the prior reasoning · it runs in parallel with siblings.
`reviewer` and `qa` pass the first two — a reviewer that watched the code being written is
anchored to it. Nothing else in the set passes any.

The stack five are the subtle case: `python-dev.md` is *Tech stack · LLM integration standards ·
RAG pipeline standards · Quality rules* — a standard, not a procedure. As a slash command it
only works if you remember to type `/python-dev` before writing Python. As a guideline loaded by
context, it simply applies.

**Also drop the verdict-line orchestration protocol from all nine.** It was built for a
hand-rolled dispatcher; the harness now does fan-out natively. It is dead weight in every file.

---

## Target architecture

```
~/$KIT/
  README.md                      what lives where · how to add a skill · how to add an adapter
  STANDARD.md                    S-01 + S-02: the skill format and the adapter contract
  install.sh                     dispatcher: --target claude   (default; others land later)
  uninstall.sh
  core/                          TOOL-AGNOSTIC. One copy of everything. No Claude assumptions.
    guidelines/                  api · chat-api · erd · diagram-architecture · planning · triage
    personas/                    architect · python-dev · react-dev · reviewer · qa · …
    skills/
      <name>/
        SKILL.md                 frontmatter + body — model-invoked description
        commands/*.md            user-invoked entry points (optional)
        *.py                     scripts, addressed via __SKILL_DIR__
        reference/               long-form refs, loaded on demand
        templates/
  adapters/
    claude/                      THE reference implementation of STANDARD.md
      install.sh                 core/skills → ~/.claude/commands + ~/.claude/skills
      hooks/                     format-on-write.sh · guard-repo-artifacts.sh
      settings/                  fragments merged into settings.json
    codex/                       PARKED — existing skills/ + AGENTS.md kept, no installer yet
```

**Tier rule for the four `.claude` directories — content owned by exactly one:**

```
~/.claude          machine + model-agnostic craft. No client names, no client paths.
confiz/.claude     what both clients share: hooks, shared guidelines, shared permissions.
<client>/.claude   brand, client doc standards, client skills, client templates.
```

---

## Task backlog

Anchors: `0.25` = a config edit with a verification · `0.5` = a contained file move or script
with a check · `1` = a subsystem. No task over 5 days. Effort excludes review latency.

| ID | Phase | Task | Days | Pri | Depends on |
|---|---|---|---|---|---|
| I-01 | 0 Insurance | ✅ **DONE** Timestamped tarball of all four `.claude` trees + `ai-clone` + `claude-skills`, incl. `scaffold-profile.{md,json}` | 0.25 | P0 | — |
| I-03 | 0 Insurance | ✅ **DONE** Commit `claude-skills`: untracked `commands/plan/`, `uninstall.sh`, modified `README.md` + `install.sh` | 0.25 | P0 | — |
| F-01 | 1 Prereq | ✅ **DONE** Delete `~/.claude/commands` symlink, **seed the real dir from current live content first** (11 of 14 entries are ai-clone-native — 9 personas, `api-review`, `spec/` — and would have been silently deleted by installing into an empty dir), then `install.sh ~/.claude --no-profile` | 0.5 | P1 | I-01, I-03 |
| F-02 | 1 Prereq | ✅ **DONE** Verify `/plan:release`, `/scaffold:new`, `/diagram:build` resolve; scripts compile; no unresolved `__SKILL_DIR__` | 0.25 | P1 | F-01 |
| S-01 | 2 Standard | ✅ **DONE** (`STANDARD.md` Part 1) Write the **artifact format**: the guideline / skill / subagent taxonomy and its promotion test (D-05); `core/skills/<name>/` layout; `SKILL.md` frontmatter schema (`description` mandatory, prose not a path); the **entry-point vs payload rule** that stops `reference/` and `templates/` registering as commands; `__SKILL_DIR__` contract. Resolves D-04 and D-05 | 1.0 | P0 | D-04, D-05 |
| S-02 | 2 Standard | ✅ **DONE** (`STANDARD.md` Part 2) Write the **adapter contract**: what any adapter must do (discover · render · rewrite path token · verify · receipt · uninstall), which parts are optional, and the conformance checklist a new adapter is held to | 0.5 | P0 | S-01 |
| M-01 | 3 Merge | ✅ **DONE** `git mv` claude-skills out of `confiz/echostar/` to `~/$KIT`; restructure to `core/` + `adapters/`, history preserved; add `.gitignore` (`__pycache__`, `.ruff_cache`, `.DS_Store`); move this plan into the new repo | 1.0 | P0 | I-03, D-01, D-03, S-01 |
| M-02 | 3 Merge | ✅ **DONE** Import ai-clone `guidelines/` → `core/guidelines/`, landing in S-01 shape | 0.5 | P0 | M-01 |
| M-03 | 3 Merge | ✅ **DONE** Import ai-clone `adapters/claude/hooks/`; park `adapters/codex/` as-is with a README note that it has no installer | 0.25 | P0 | M-01 |
| M-04 | 3 Merge | ✅ **DONE** Import the ai-clone-only assets in S-01 shape: `spec/` skill and `api-review`. **Also relocate the 8 existing entry points to `commands/<verb>.md`** — required by the §1.3 allowlist | 0.75 | P0 | M-02 |
| M-05 | 3 Merge | ✅ **DONE** Collapse the 4 duplicate pairs — planning guidelines, plan tooling, diagram guide, ERD guide. Pick a winner, delete the loser, record why in the commit | 1.0 | P0 | M-02, M-04 |
| M-06 | 3 Merge | ✅ **DONE** De-client the shared guidelines: strip Echostar/Ecostar and Under Armour references from the diagram + ERD guides | 0.5 | P0 | M-05 |
| M-07 | 3 Merge | ✅ **DONE** Delete superseded snapshots: `ai-clone/tools/plan/`, `ai-clone/adapters/claude/commands/{diagram,eval,scaffold}` | 0.25 | P0 | M-05 |
| M-08 | 3 Merge | ✅ **DONE** **Triage the 9 personas per D-05** — 5 → `core/guidelines/`, 2 → `core/skills/`, 2 → subagents with real frontmatter. Strip the dead `## Input protocol` / verdict-line orchestrator scaffolding from all nine | 1.0 | P0 | M-01, S-01 |
| M-09 | 3 Merge | ✅ **DONE** *(unplanned)* Apply the promotion test to the kit itself: cut `decomposer` (Gate 2 of `plan` with the S/M/L sizing plan's own reference forbids); `api-review` skill → subagent | 0.5 | P0 | M-08 |
| M-10 | 3 Merge | ✅ **DONE** *(unplanned)* One reviewer, N guidelines: cut `api-review`, `reviewer` gains a standards dimension, move the six `*_STANDARDS.md` from `scaffold/templates/` to `core/guidelines/`, rewire scaffold via `__GUIDELINES_DIR__`. Fixes a **5th duplicate pair** M-05 missed — two byte-identical copies of the 395-line API standards | 1.0 | P0 | M-09 |
| M-11 | 3 Merge | ✅ **DONE** *(unplanned)* `architect` → guideline (rules, not a procedure); cut `spec` (671 lines, never invocable, 2 unique checks) | 0.5 | P0 | M-10 |
| M-12 | 3 Merge | ✅ **DONE** *(unplanned)* Make `core/` genuinely tool-independent — the first leak test was a grep too narrow to catch it. Adds `__KIT_DATA_DIR__`, `__GUIDELINES_DIR__`, `{{cmd:…}}`, `{{args}}`, `arguments:` frontmatter | 1.5 | P0 | M-08 |
| M-13 | 3 Merge | ✅ **DONE** *(unplanned)* Skill READMEs back beside their skills (`docs/skills/` had drifted in 20 commits); `README.md` classified as documentation in the standard; `applies_to` on all 12 guidelines; `python-genai` → `python-llm` | 0.5 | P0 | M-12 |
| A-02 | 4 Claude adapter | ✅ **DONE** Write `adapters/claude/install.sh`. **The current `install.sh` is broken** — it reads `REPO_ROOT/commands/`, which M-01 renamed to `core/skills/`. Must: render all three kinds (guideline → skills/ only; skill → skills/ + commands/; subagent → agents/); **register only declared entry points, never payload**; resolve all five markers and fail on an unresolvable `{{cmd:…}}`; honour obligation 11 (kit data dir, never overwritten); append `applies_to` to rendered descriptions; verify, receipt, replace-not-merge | 1.5 | P0 | S-02, M-13 |
| A-04 | 4 Claude adapter | ✅ **DONE** Thin top-level `install.sh --target claude` dispatcher — defaults to claude, errors clearly on an unknown target. Establishes the seam now so adding one later is additive | 0.25 | P1 | A-02 |
| A-05 | 4 Claude adapter | ✅ **DONE** Repair the two mis-shaped skills into S-01 form: dead `~/.claude/skills/release-plan.md`, misfiled UA `skills/brand-guidelines.md` | 0.5 | P2 | S-01 |
| A-06 | 4 Claude adapter | ✅ **DONE** (13/13, `adapters/claude/conformance.sh`) Run the S-02 conformance checklist against the Claude adapter; fix whatever fails. This is the control that stops Claude assumptions leaking into `core/` | 0.5 | P0 | A-02 |
| A-07 | 4 Claude adapter | ✅ **DONE** *(unplanned, found by A-06)* Close the three conformance gaps the checklist found: **obligation 10 was never implemented** (`--uninstall`), the adapter had no README stating which kinds it supports, and two `core/` READMEs still named `.claude` paths | 0.5 | P0 | A-06 |
| C-01 | 5 Re-tier | ✅ **DONE** `~/.claude/CLAUDE.md`: strip client content; replace the ~930-line always-on import block with on-demand pointers | 0.5 | P0 | M-06 |
| C-02 | 5 Re-tier | ✅ **DONE** Activate `confiz/.claude`: shared guideline imports, both guard hooks, shared `additionalDirectories`, shared permissions | 0.5 | P0 | C-01 |
| C-03 | 5 Re-tier | ✅ **DONE** `~/.claude/settings.json`: strip the ~40 accreted one-off allow rules; relocate UA-specific ones; resolve the plugin-tier split (ponytail in confiz vs the rest global) | 0.5 | P1 | C-02 |
| C-04 | 5 Re-tier | ✅ **DONE** Echostar `.claude`: drop empty `"allow": []`, inherit the guard hook from the confiz tier, keep only Echostar-owned guidelines; `package` skill conforms to S-01 | 0.25 | P1 | C-02 |
| C-05 | 5 Re-tier | ✅ **DONE** UA `.claude`: same treatment; drop the redundant `additionalDirectories`; brand guide becomes a real skill | 0.25 | P1 | C-02, A-05 |
| C-06 | 5 Re-tier | ✅ **DONE** Delete cruft: the `~/.claude/{guidelines,agents}` symlinks, `settings.json.bak-20260714-precleanup`, stray `.DS_Store` | 0.25 | P2 | C-01 |
| V-01 | 6 Verify | ✅ **DONE** (14/14, `confiz/.claude/verify-tiers.sh`) Fresh session in each of the three project roots: skill list correct, no cross-client content loaded, guard hook fires on a `gitlab/` write | 0.5 | P0 | C-04, C-05 |
| C-07 | 5 Re-tier | ✅ **DONE** *(unplanned, found by V-01)* The Echostar tier still `@`-imported all three of its guidelines on every session — **1,010 always-on lines**, the same defect C-01 fixed one tier up, and asymmetric with UA whose brand guide was already a skill. Two new project skills (`echostar-style`, `chat-api`); Echostar now loads 159 lines | 0.5 | P0 | C-04, V-01 |
| V-03 | 6 Verify | ✅ **DONE** `README.md`: what lives where, how to add a skill, **how to add an adapter**. Load-bearing now that Codex is deferred — this document is what keeps the second adapter cheap | 0.5 | P0 | A-04, S-02 |
| V-04 | 6 Verify | ✅ **DONE** Orphan sweep — grep every CLAUDE.md, settings file and skill for stale `ai-clone/` and `confiz/echostar/claude-skills/` paths | 0.5 | P0 | C-06, V-03 |
| X-01 | 6 Verify | **Decommission ai-clone** — confirm all 17 inbound reference sites are repointed, then remove the directory. Ordering is not optional: `format-on-write.sh` fires on every Write/Edit globally, so a dead hook path breaks all editing | 0.25 | P0 | V-04 |

**Totals — 35 tasks · 19.75 days · 27 P0 · 34 tasks / 19.50 days complete (97%)**

| Phase | Tasks | Days | P0 | Status |
|---|---|---|---|---|
| 0 Insurance | 2 | 0.50 | 2 | ✅ complete |
| 1 Prereq | 2 | 0.75 | 0 | ✅ complete |
| 2 Standard | 2 | 1.50 | 2 | ✅ complete |
| 3 Merge | 13 | 9.25 | 13 | ✅ complete — 5 unplanned |
| 4 Claude adapter | 5 | 3.25 | 3 | ✅ complete — 1 unplanned |
| 5 Re-tier | 7 | 2.75 | 3 | ✅ complete — 1 unplanned |
| 6 Verify | 4 | 1.75 | 4 | ⬜ 3/4 done |

---

## Verification record

Two scripts, both rerunnable, both checking properties rather than strings already known to
be present. The distinction matters: every check in this project that passed by matching a
string I had just written found nothing, and every check that asked *does this resolve, does
this count match, does this survive a round trip* found a real defect.

### A-06 — adapter conformance · `adapters/claude/conformance.sh` · **13/13**

Runs `STANDARD.md` §2.4 (per-install verification) and §2.5 (the adapter itself) against a
throwaway target, so nothing it does can touch `~/.claude`.

| | Check |
|---|---|
| §2.4 | install exits 0 on a clean target · declared entry points == registered · zero surviving markers · every rendered `/skill:verb` resolves to an installed command · kit data dir byte-identical after install · every installed `.py` parses · receipt lists all four kinds |
| §2.5 | installing twice produces an identical tree · an artifact deleted from `core/` disappears from the install · uninstall removes exactly the receipt contents and keeps the data dir · leak test over `core/` · adapter README states which kinds it supports · obligations 1–10 implemented and annotated |

**First run: 11/13.** The two failures became A-07:

1. **Obligation 10 was never implemented.** There was no uninstall at all. It had gone
   unnoticed because nothing had ever tried to uninstall — the obligation was written in the
   standard and simply not carried out.
2. **The leak test found two `core/` files naming `.claude`** — `diagram/README.md` and
   `scaffold/README.md`. Earlier leak greps had covered `SKILL.md` and scripts but not
   maintainer READMEs, which are still files under `core/`.

Also surfaced: obligations 3, 4 and 9 were implemented but unannotated, so nothing tied the
code to the contract. A header reading `Obligations 3–5` is not an annotation of obligation 3
if the check — or a reader — looks for it by number.

### V-01 — what a fresh session resolves · `~/confiz/.claude/verify-tiers.sh` · **14/14**

Resolves the `CLAUDE.md` chain per project root including transitive `@`-imports, then checks
isolation, the registered skill set, and the guard hook by actually firing it with six
payloads (artifact into a protected repo, artifact into the design workspace, source code
inside a protected repo — each per client).

Lives in the cross-client tier because that is the only tier that legitimately knows both
clients; putting it in `agent-kit` would be a client leak, putting it in `~/.claude` would
put client names back in the machine tier.

**Finding → C-07.** The always-on line count per root was:

| Root | Before | After |
|---|---|---|
| Echostar | 1,010 | 159 |
| Under Armour | 88 | 88 |

The Echostar tier still `@`-imported all three of its guidelines unconditionally — the same
defect C-01 fixed at the machine tier, one tier down, and invisible until the chain was
resolved transitively. It was also asymmetric: UA's brand guide had already become a skill in
C-05, so one client paid for its guidelines only when it used them and the other paid always.
Fixed by two new project-tier skills, `echostar-style` and `chat-api`; the `package` skill
already carried the third.

Note the first version of this script undercounted, missing `chat-api-guidelines.md` because
its `@` reference sits mid-bullet rather than at the start of a line. A verifier with the
wrong idea of what counts is worse than none — it reports a pass over the thing it cannot see.
