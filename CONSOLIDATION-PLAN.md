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
| I-01 | 0 Insurance | Timestamped tarball of all four `.claude` trees + `ai-clone` + `claude-skills`, incl. `scaffold-profile.{md,json}` | 0.25 | P0 | — |
| I-03 | 0 Insurance | Commit `claude-skills`: untracked `commands/plan/`, `uninstall.sh`, modified `README.md` + `install.sh` | 0.25 | P0 | — |
| F-01 | 1 Prereq | ✅ **DONE** Delete `~/.claude/commands` symlink, **seed the real dir from current live content first** (11 of 14 entries are ai-clone-native — 9 personas, `api-review`, `spec/` — and would have been silently deleted by installing into an empty dir), then `install.sh ~/.claude --no-profile` | 0.5 | P1 | I-01, I-03 |
| F-02 | 1 Prereq | ✅ **DONE** Verify `/plan:release`, `/scaffold:new`, `/diagram:build` resolve; scripts compile; no unresolved `__SKILL_DIR__` | 0.25 | P1 | F-01 |
| S-01 | 2 Standard | ✅ **DONE** (`STANDARD.md` Part 1) Write the **artifact format**: the guideline / skill / subagent taxonomy and its promotion test (D-05); `core/skills/<name>/` layout; `SKILL.md` frontmatter schema (`description` mandatory, prose not a path); the **entry-point vs payload rule** that stops `reference/` and `templates/` registering as commands; `__SKILL_DIR__` contract. Resolves D-04 and D-05 | 1.0 | P0 | D-04, D-05 |
| S-02 | 2 Standard | ✅ **DONE** (`STANDARD.md` Part 2) Write the **adapter contract**: what any adapter must do (discover · render · rewrite path token · verify · receipt · uninstall), which parts are optional, and the conformance checklist a new adapter is held to | 0.5 | P0 | S-01 |
| M-01 | 3 Merge | `git mv` claude-skills out of `confiz/echostar/` to `~/$KIT`; restructure to `core/` + `adapters/`, history preserved; add `.gitignore` (`__pycache__`, `.ruff_cache`, `.DS_Store`); move this plan into the new repo | 1.0 | P0 | I-03, D-01, D-03, S-01 |
| M-02 | 3 Merge | Import ai-clone `guidelines/` → `core/guidelines/`, landing in S-01 shape | 0.5 | P0 | M-01 |
| M-03 | 3 Merge | Import ai-clone `adapters/claude/hooks/`; park `adapters/codex/` as-is with a README note that it has no installer | 0.25 | P0 | M-01 |
| M-04 | 3 Merge | Import the ai-clone-only assets in S-01 shape: `spec/` skill and `api-review`. **Also relocate the 8 existing entry points to `commands/<verb>.md`** — required by the §1.3 allowlist | 0.75 | P0 | M-02 |
| M-05 | 3 Merge | Collapse the 4 duplicate pairs — planning guidelines, plan tooling, diagram guide, ERD guide. Pick a winner, delete the loser, record why in the commit | 1.0 | P0 | M-02, M-04 |
| M-06 | 3 Merge | De-client the shared guidelines: strip Echostar/Ecostar and Under Armour references from the diagram + ERD guides | 0.5 | P0 | M-05 |
| M-07 | 3 Merge | Delete superseded snapshots: `ai-clone/tools/plan/`, `ai-clone/adapters/claude/commands/{diagram,eval,scaffold}` | 0.25 | P0 | M-05 |
| M-08 | 3 Merge | **Triage the 9 personas per D-05** — 5 → `core/guidelines/`, 2 → `core/skills/`, 2 → subagents with real frontmatter. Strip the dead `## Input protocol` / verdict-line orchestrator scaffolding from all nine | 1.0 | P0 | M-01, S-01 |
| A-02 | 4 Claude adapter | Rework `install.sh` → `adapters/claude/install.sh`: renders `core/skills` into **both** `~/.claude/commands` (user-invoked) and `~/.claude/skills` (model-invoked); **registers only declared entry points, never payload**; keeps the existing verification, receipt and replace-not-merge semantics | 1.0 | P0 | S-02, M-04 |
| A-04 | 4 Claude adapter | Thin top-level `install.sh --target claude` dispatcher — defaults to claude, errors clearly on an unknown target. Establishes the seam now so adding one later is additive | 0.25 | P1 | A-02 |
| A-05 | 4 Claude adapter | Repair the two mis-shaped skills into S-01 form: dead `~/.claude/skills/release-plan.md`, misfiled UA `skills/brand-guidelines.md` | 0.5 | P2 | S-01 |
| A-06 | 4 Claude adapter | Run the S-02 conformance checklist against the Claude adapter; fix whatever fails. This is the control that stops Claude assumptions leaking into `core/` | 0.5 | P0 | A-02 |
| C-01 | 5 Re-tier | `~/.claude/CLAUDE.md`: strip client content; replace the ~930-line always-on import block with on-demand pointers | 0.5 | P0 | M-06 |
| C-02 | 5 Re-tier | Activate `confiz/.claude`: shared guideline imports, both guard hooks, shared `additionalDirectories`, shared permissions | 0.5 | P0 | C-01 |
| C-03 | 5 Re-tier | `~/.claude/settings.json`: strip the ~40 accreted one-off allow rules; relocate UA-specific ones; resolve the plugin-tier split (ponytail in confiz vs the rest global) | 0.5 | P1 | C-02 |
| C-04 | 5 Re-tier | Echostar `.claude`: drop empty `"allow": []`, inherit the guard hook from the confiz tier, keep only Echostar-owned guidelines; `package` skill conforms to S-01 | 0.25 | P1 | C-02 |
| C-05 | 5 Re-tier | UA `.claude`: same treatment; drop the redundant `additionalDirectories`; brand guide becomes a real skill | 0.25 | P1 | C-02, A-05 |
| C-06 | 5 Re-tier | Delete cruft: the `~/.claude/{guidelines,agents}` symlinks, `settings.json.bak-20260714-precleanup`, stray `.DS_Store` | 0.25 | P2 | C-01 |
| V-01 | 6 Verify | Fresh session in each of the three project roots: skill list correct, no cross-client content loaded, guard hook fires on a `gitlab/` write | 0.5 | P0 | C-04, C-05 |
| V-03 | 6 Verify | `README.md`: what lives where, how to add a skill, **how to add an adapter**. Load-bearing now that Codex is deferred — this document is what keeps the second adapter cheap | 0.5 | P0 | A-04, S-02 |
| V-04 | 6 Verify | Orphan sweep — grep every CLAUDE.md, settings file and skill for stale `ai-clone/` and `confiz/echostar/claude-skills/` paths | 0.5 | P0 | C-06, V-03 |
| X-01 | 6 Verify | **Decommission ai-clone** — confirm all 17 inbound reference sites are repointed, then remove the directory. Ordering is not optional: `format-on-write.sh` fires on every Write/Edit globally, so a dead hook path breaks all editing | 0.25 | P0 | V-04 |

**Totals — 28 tasks · 14.25 days · 20 P0**

| Phase | Tasks | Days | P0 |
|---|---|---|---|
| 0 Insurance | 2 | 0.50 | 2 |
| 1 Prereq | 2 | 0.75 | 0 |
| 2 Standard | 2 | 1.50 | 2 |
| 3 Merge | 8 | 5.25 | 8 |
| 4 Claude adapter | 4 | 2.25 | 2 |
| 5 Re-tier | 6 | 2.25 | 2 |
| 6 Verify | 4 | 1.75 | 4 |

### ai-clone inbound reference inventory — the decommission checklist

ai-clone is **fully absorbed**: `agents/` → personas triage (M-08), `guidelines/` →
`core/guidelines/` (M-02), `adapters/` → `adapters/` (M-03), `tools/plan/` → deleted as a
duplicate (M-05). Nothing survives it. But 17 sites point at it and must be repointed first.

| Reference | Count | Repointed by | If it dies first |
|---|---|---|---|
| Hook commands in settings (`format-on-write.sh`, `guard-repo-artifacts.sh` ×2) | 3 | C-02, C-03 | **`format-on-write` fires on every Write/Edit globally — all editing breaks** |
| `@`-imports of `guidelines/` across 3 CLAUDE.md files | 6 | C-01, C-04, C-05 | Guidelines silently stop loading |
| `additionalDirectories` entries | 2 | C-03, C-05 | Permission failures |
| Symlinks `agents` · `commands` · `guidelines` | 3 | F-01, C-06 | Personas and commands disappear |
| Persona files `@`-importing `agents/*.md` | 10 files | M-08 | Self-referential; resolved by the triage |

---

## Phase exit gates

Binary — every line true, or the phase is not done.

**Phase 0 — Insurance**
- [ ] Tarball exists and restores cleanly into a scratch directory
- [ ] `git -C claude-skills status --short` is empty

**Phase 1 — Prereq**
- [ ] `~/.claude/commands` is a real directory, not a symlink
- [ ] `/plan:release` appears in the skill list of a fresh session
- [ ] `~/.claude/scaffold-profile.md` still contains your filled-in values
- [ ] Installed `scaffold/new.py` is byte-identical to the repo copy

**Phase 2 — Standard**
- [ ] `STANDARD.md` states the skill format and the adapter contract, and resolves D-04
- [ ] Every required and optional field of `SKILL.md` frontmatter is specified
- [ ] The entry-point vs payload boundary is stated as a rule an installer can mechanically apply
- [ ] The contract names which obligations an adapter may render as a *subset* — the clause that makes a second adapter possible
- [ ] A conformance checklist exists that a new adapter can be run against

**Phase 3 — Merge**
- [ ] `~/$KIT` exists; `git log --follow` on a moved file shows pre-move history
- [ ] Nothing remains under `confiz/echostar/claude-skills/`
- [ ] Each of the 4 duplicate pairs has exactly one surviving copy
- [ ] `grep -ri 'ecostar\|echostar\|under.armour' core/guidelines/` returns nothing
- [ ] Every `core/skills/*/` matches the S-01 layout
- [ ] All 9 personas are classified guideline / skill / subagent; the 2 subagents have valid frontmatter and appear in a live session's agent list
- [ ] `grep -rn 'Input protocol\|Verdict line' core/` returns nothing

**Phase 4 — Claude adapter**
- [ ] `install.sh --target claude` completes; receipt written
- [ ] Every `core/skills/*/SKILL.md` has valid frontmatter, and every `description` is prose rather than a path
- [ ] **Installed command count equals declared entry-point count** — zero payload files registered (baseline to beat, measured after Phase 1: 18 real of 40 registered — 22 payload)
- [ ] Zero unresolved `__SKILL_DIR__` tokens in the install target
- [ ] **No file under `core/` references a Claude-specific path, filename or invocation syntax** (`~/.claude`, `CLAUDE.md`, `/skill:cmd`) — the leak test
- [ ] The S-02 conformance checklist passes against the Claude adapter

**Phase 5 — Re-tier**
- [ ] No string appears in two tiers with two values
- [ ] An Under Armour session loads zero Echostar bytes
- [ ] `~/.claude/settings.json` contains no client-specific hostname, script or branch name

**Phase 6 — Verify**
- [ ] All three project roots open clean, correct skill list, correct guidelines
- [ ] `README.md` documents adding an adapter well enough to start Codex without reopening this plan
- [ ] Orphan sweep returns zero stale paths
- [ ] `grep -rn 'ai-clone'` across all four `.claude` trees returns nothing
- [ ] A Write and an Edit both succeed after the hook paths move — checked *before* ai-clone is removed
- [ ] `~/ai-clone` no longer exists

---

## Deferred

### A-03 — Codex adapter installer  ·  1.0 d  ·  was P1

**Reason for deferral:** you chose Claude as the first and only adapter for this pass.

**Full original analysis, kept so it can return without redoing the thinking.** Codex today
has `adapters/codex/skills/` (nine personas) and a hand-written `AGENTS.md`, and no installer
at all. The work is to write `adapters/codex/install.sh` rendering the same `core/skills` into
the Codex layout, plus regenerating `AGENTS.md` from `core/guidelines` instead of maintaining
it by hand. The 1.0 d was always **directional** — a guess against a greenfield target, not a
measurement against existing code. Re-estimate before scheduling it.

**What keeps this cheap when it returns:** S-02 (the adapter contract), A-04 (the dispatcher
seam) and V-03 (the how-to-add-an-adapter section) all ship in this pass specifically so that
Codex is an addition, not a refactor. None of them were deferred.

### V-02 — Verify the Codex adapter installs and resolves  ·  0.25 d  ·  was P1

**RULE — paired with A-03.** V-02 exists only to verify A-03. Deferring A-03 makes V-02
pointless; **reinstating A-03 without V-02 is not allowed** — an unverified second adapter is
how `core/` silently acquires tool-specific assumptions.

**Blast radius swept.** Removed from the plan alongside these two: the `--target all` exit-gate
line (now `--target claude`), the "both receipts" check, and the Phase 6 codex smoke test.
`adapters/codex/` itself is **kept** in the tree by M-03, parked with a README note, so the
existing persona content is not lost.

---

## Gate 3 review notes — overlaps, gaps, judgement calls

- **F-01 vs A-02 (partial overlap, kept deliberately).** F-01 reinstalls with the *old*
  installer; A-02 replaces it days later. About 0.25 d is spent twice. Kept, because running a
  143-line-stale `/scaffold:new` for the duration of a multi-day migration is the larger risk.
- **Ordering change vs the previous draft.** The standard moved ahead of the merge. This
  removed a 1.5 d conformance-rewrite pass and replaced it with a 0.5 d conformance *check*
  (A-06), at the cost of +0.5 d spread across M-02 and M-04, which now land files in final
  shape. Net −0.5 d, and one fewer touch per file.
- **The one-adapter risk, and its control.** With only Claude to test against, `core/` can
  quietly acquire Claude-shaped assumptions and nobody notices until Codex starts. Two controls
  ship for this: the S-02 subset-rendering clause, and the Phase 4 leak test — a mechanical
  grep, not a judgement call.
- **Gap found while executing F-01 — the stopgap would have deleted 11 commands.** F-01 said
  "delete the symlink, create a real dir, re-run install.sh". But `install.sh` only creates the
  four skills that exist in `claude-skills`; 11 of the 14 live entries are ai-clone-native
  (9 personas, `api-review.md`, `spec/`) and would have vanished silently. Corrected in flight
  by seeding the real directory from the current live content before installing over it. The
  lesson generalises to M-08 and A-02: **`claude-skills` was never the whole live command set**,
  and any step that treats it as authoritative loses the ai-clone-native half.
- **Cut — I-02, `git init` ai-clone.** Challenged and removed. The I-01 tarball already provides
  the restore point, and ai-clone is dissolved within days; per-commit granularity on a directory
  nothing is incrementally edited buys nothing over a snapshot. −0.25 d.
- **Gap found by that challenge — no decommission task existed.** The plan absorbed ai-clone but
  never deleted it, and 17 live sites point at it. Three are load-bearing *during* the migration:
  `format-on-write.sh` fires on every Write/Edit globally, so deleting ai-clone before C-02/C-03
  repoint the hooks breaks all editing in every project. Now X-01, gated on V-04, with the
  inventory table above as its checklist.
- **Gap found — the personas were never triaged (see D-05).** M-02 assumed a straight
  `agents/` → `core/personas/` import. It is not an import: five files are guidelines, two are
  skills, two are subagents, and all nine carry dead orchestrator scaffolding. Split into M-02
  (guidelines, 0.5 d) and M-08 (persona triage, 1.0 d). +0.75 d — the largest single correction
  in this plan, and it came from a question, not from re-reading the plan.
- **Gap found — 20 phantom commands (see D-04).** Not visible from reading the plan or the
  install script; only from listing what a live session actually registers. `install.sh` strips
  the root `README.md` but never walks into `reference/` or `templates/`, so 20 payload files
  are invocable today. It is a one-line filter to fix once S-01 states the rule — but it would
  have survived the whole migration unnoticed, because every phase before Phase 4 moves those
  files around without ever asking what they register as.
- **Gap found — profile data loss.** `install.sh` runs `profile.py --generate`, which can
  overwrite a filled-in `scaffold-profile.md`. F-01 now specifies `--no-profile`; I-01 backs
  the file up regardless.
- **Gap found — client-owned skills.** Echostar's `package` and UA's brand guide stay
  client-side but must still adopt S-01, or you have two skill conventions again within a
  month. Covered by C-04 and C-05.
- **Fixed vs volume-driven cost.** Phases 0, 1, 2, 5 and 6 are fixed. Phase 3 and Phase 4
  scale with skill count (5 skills + 9 personas + 1 spec today). Adding skills before Phase 4
  lands makes the migration bigger — **hold new skills until then.**
- **No directional estimates remain in the active plan.** The only one, A-03, is deferred.
  Everything scheduled was sized against files that exist.
