# claude-skills

A portable, installable set of [Claude Code](https://claude.com/claude-code) skills
(slash commands). Clone it, run `./install.sh`, and the commands become available in your
Claude Code sessions — with no machine-specific paths baked in.

## Skills

**[`scaffold`](commands/scaffold/README.md)** — stand up a Databricks repo and keep its
config out of your way.

| Command | What it does |
|---|---|
| `/scaffold:profile` | Set up the org/project values shared by every repo (branding, team, CI/CD, policies) once per install (`scaffold-profile.md` → profile). |
| `/scaffold:new` | Scaffold a new Databricks repo (type-driven wizard: `api` · `etl` · `job` · `agent` · `genie`). |
| `/scaffold:add` | Add one **aspect** — the `cicd` deploy pipeline, or the `api` surface (`/v1/health` + `/v1/info`) — to a repo that already exists. |
| `/scaffold:configure` | Fill the remaining per-repo `TODO_SET_*` placeholders a scaffolded repo ships with (`CONFIG.md` → repo). |

**[`eval`](commands/eval/README.md)** — give a use case its own evaluation, scored by a
shared engine it never copies.

| Command | What it does |
|---|---|
| `/eval:new` | Scaffold `evaluation/` (spec + run wrapper + starter datasets) in the repo that owns the eval. |

**[`diagram`](commands/diagram/README.md)** — `.drawio` diagrams that are verified before
they are shown.

| Command | What it does |
|---|---|
| `/diagram:build` | Build a diagram from the reference spec + the project's brand, then check, render, and self-review it. |
| `/diagram:review` | Audit an existing `.drawio`: geometry check + rendered read-through + verdict. |

Each skill's own `README.md` covers it in depth — the scaffold two-level config model and
repo types, the eval engine/spec split, the diagram verify loop.

**A repo is a skeleton plus aspects.** An **aspect** is one named slice of a repo, defined once
in `scaffold/aspects.py`. `/scaffold:new` applies a type's standard set to a fresh tree;
`/scaffold:add` puts a single aspect into a repo that already exists (including repos this tool
never made) — writing only that aspect's files, never overwriting silently, and printing the
wiring a copy cannot do. Only two are choosable, `cicd` and `api`; a `.gitignore` and a
regenerated `CONFIG.md` come along automatically, because they are hygiene rather than
decisions.

**Two levels of configuration.** The **profile** holds what's constant across a team's
repos — collected once and baked into every scaffold. **`CONFIG.md`** holds what's genuinely
per-repo (workspace hosts, service principals, repo URL, catalog, table prefix). Anything you
leave blank in the profile simply stays a per-repo `TODO_SET_*` for `configure` to fill.

## Install

```bash
git clone <this-repo-url> claude-skills
cd claude-skills
./install.sh
```

`install.sh` asks where to install and accepts either a `.claude` directory or a project
root (it appends `/.claude`):

```bash
./install.sh ~/.claude            # for every project on this machine
./install.sh /path/to/my-project  # just that project (installs to its .claude/)
```

It copies the skills into `<target>/.claude/commands/` and rewrites the `__SKILL_DIR__`
install-time path token — per skill, to that skill's installed directory — so the slash
commands find their scripts. Re-run it any time to update an install.

It then generates a fill-in **profile sheet** at `<target>/.claude/scaffold-profile.md`.
Fill in the values shared across your work (all optional) and apply them with
`/scaffold:profile`. The profile is shared by every installed skill — scaffold bakes its
values into each new repo, `eval` reads the engine path from it, `diagram` reads the output
folder, brand guide, and draw.io binary. Each skill declares its own fields in its
`profile_fields.py`, and they appear in the sheet automatically. Skip the sheet with:

```bash
./install.sh ~/.claude --no-profile   # install only; set up the profile later
```

Re-run `python3 <target>/.claude/commands/scaffold/profile.py` any time to update the
profile (edit the sheet, then apply).

## Where scaffolded repos land

`/scaffold:new` creates the new repo in **`$SCAFFOLD_OUTPUT_DIR`**, or the profile's
`output_dir`, or the current directory if both are unset (override per-run with
`--output-dir`). Set a default via the env var:

```bash
export SCAFFOLD_OUTPUT_DIR="$HOME/repos"
```

or set `output_dir` once in the profile sheet and apply it with `/scaffold:profile`.
Resolution order: `--output-dir` > `$SCAFFOLD_OUTPUT_DIR` > profile `output_dir` > CWD.

## Layout

```
commands/            one folder per slash-command skill (mirrors .claude/commands/)
  scaffold/          profile.(md|py) + new.(md|py) + add.(md|py) + configure.(md|py)
                     + aspects.py + config_tokens.py + templates/
  eval/              new.(md|py) + profile_fields.py + templates/
  diagram/           build.md + review.md + check.py + render.py
                     + profile_fields.py + reference/
install.sh           copies commands/ into a target .claude, fixes paths, seeds the profile
scaffold-profile.{md,json}   generated per-install profile (in .claude/ root; gitignored)
```

To add a skill, drop a new folder under `commands/` following the same shape; `install.sh`
picks it up automatically. The shape is: one `<command>.md` per slash command (`/<skill>:<command>`),
its script beside it, `__SKILL_DIR__` wherever a path to that script is needed, real files
with `TPLVAR_*` / `TODO_SET_*` tokens under `templates/`, an optional `profile_fields.py`
for any shared-profile values the skill needs, and a `README.md`. Never hardcode a machine
path, an org name, or a project name — resolve it from a flag, an env var, or the profile.

## Design

**Generated files are real files.** Everything a skill writes lives under its `templates/`
as an actual file carrying `TPLVAR_*` / `TODO_SET_*` tokens; the Python is pure
orchestration. `scaffold`'s `new.py` builds every repo type through one path
(`copytree(templates/<type>/)` + token substitution) driven by a small table, so adding a
type is a new `templates/<type>/` dir plus one row in the maps.

**One definition, two directions.** The composable slices of a repo live in one registry
(`scaffold/aspects.py`) that both the create path and the add-to-existing path go through, so
an aspect cannot drift into meaning two different things. Adding one is a single entry there —
`/scaffold:new`, `/scaffold:add` and `add.py --detect` all pick it up untouched.

**Values are resolved, never hardcoded.** Every skill resolves each value in the same order
— an explicit CLI flag, then an environment variable where one makes sense, then the shared
install **profile** (`scaffold-profile.json`), then a `TODO_SET_*` placeholder or a
documented fallback. That is why nothing here carries a machine path, an org name, or a
project name: `scaffold` leaves unresolved values for `/scaffold:configure`, `eval` falls
back to auto-detecting the engine checkout, `diagram` falls back to PATH and the reference
defaults.

**The profile is shared, but each skill owns its fields.** `scaffold/profile.py` holds the
scaffold fields and discovers every sibling skill's `profile_fields.py`, so one sheet covers
the whole install and a skill that is not installed contributes nothing.
