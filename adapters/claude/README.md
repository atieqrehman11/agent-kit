# Claude adapter

Installs `core/` into a `.claude` directory. This is the reference implementation of
[`STANDARD.md`](../../STANDARD.md) Part 2 — every obligation is annotated in
[`install.py`](install.py) with the number it satisfies.

```
python3 adapters/claude/install.py [TARGET] [--dry-run] [--uninstall]
```

`TARGET` defaults to `~/.claude`; a path without a `.claude` basename gets one appended.

---

## Kinds supported

All three. Nothing is skipped, so the §2.2 subset clause is not exercised here.

| Kind | Rendered as | Invocable how |
|---|---|---|
| **guideline** | `guidelines/<name>.md` — canonical copy, what `__GUIDELINES_DIR__` points at<br>`skills/<name>/SKILL.md` — registration copy, `applies_to` folded into the description | Model-invoked from context. **No slash command** — a constraint is not something you run |
| **skill** | `skills/<name>/` — `SKILL.md` plus all payload; `__SKILL_DIR__` resolves here<br>`commands/<name>/<verb>.md` — one file per declared command | `/<name>:<verb>`, plus model-invoked via `SKILL.md` |
| **subagent** | `agents/<name>.md` | Dispatched by the Agent tool under its `name` |

A guideline is written **twice on purpose**: once in canonical form for skills that read it
as a file, once in Claude's registration format. Both are generated and both are replaced
wholesale on every install, so neither can drift from `core/`.

## Marker resolution

| Marker | Resolves to |
|---|---|
| `__SKILL_DIR__` | `<target>/skills/<name>` |
| `__GUIDELINES_DIR__` | `<target>/guidelines` |
| `__KIT_DATA_DIR__` | `<target>` — see below |
| `__PROJECT_SCOPE_DIR__` | `.claude` — Claude's per-project config directory, so a project-scoped profile sits beside that project's `CLAUDE.md` |
| `__ORG_PREFIX__` | `"<org> "` from the install-wide `scaffold-profile.json`, or nothing when unset |
| `{{cmd:<skill>:<verb>}}` | `/<skill>:<verb>` |
| `{{args}}` | `$ARGUMENTS` |

A surviving marker fails the install. A `{{cmd:…}}` naming a skill or verb that does not
exist fails it **before the first byte is written**.

## Kit data dir (obligation 11)

The target *is* the kit data dir. This is deliberate: `~/.claude` already holds the user's
own state, and the scaffold profile sheet lives beside it. Consequences:

- Only `guidelines/`, `skills/`, `commands/` and `agents/` are ever replaced. Everything
  else in the target is untouched.
- The profile sheet is hashed before and after; a change fails verification.
- Verification scans **only those four directories** — walking the whole target once
  "found" unresolved markers inside a session transcript that happened to discuss them.

## Uninstall

`--uninstall` reads `.agent-kit-install.json` and removes exactly what it lists. It is
driven by the receipt, not by a re-scan of `core/`, so an artifact deleted from `core/`
since the install is still removed and a file the user added by hand is still left alone.
Created directories are removed only once empty. The kit data dir is never removed.

## Hooks

`hooks/` holds two shell hooks the installer does **not** wire up — settings are the user's
tier to own, so they are referenced from a `settings.json` by absolute path:

| Hook | Fires on | Does |
|---|---|---|
| `format-on-write.sh` | `PostToolUse` Write/Edit | formats the written file for its language |
| `guard-repo-artifacts.sh <segment>` | `PreToolUse` Write/Edit | blocks writes into a real deployed repo directory (`gitlab/`, `github/`) |

## Workflows

`workflows/` holds orchestration scripts. Like `hooks/`, the installer does **not** touch
them — they are invoked by path, not registered.

| Workflow | Does |
|---|---|
| `deliver.js` | Runs several requirements through the `deliver` gates at once, one isolated git worktree each, and returns a roll-up that puts the blocked ones first |

```
Workflow({ scriptPath: "<kit>/adapters/claude/workflows/deliver.js",
           args: ["add rate limiting to the reports endpoint",
                  "externalise the summariser prompt"] })
```

**Why this is here and not in `core/`.** Worktree isolation, background execution and
parallel fan-out are properties of this tool, not of the standard —
[`STANDARD.md` §1.7](../../STANDARD.md#117-what-may-not-appear-in-core) keeps them out of
`core/`. The gate logic they orchestrate lives in `core/skills/deliver/`, so an adapter
without a workflow engine still gets the gates through `/deliver:feature`, one requirement at
a time. A gate that needed to know it was being run in parallel would mean the split is wrong.

One requirement does not need this. Use `/deliver:feature` and skip the worktree overhead.
