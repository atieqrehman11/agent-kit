# claude-skills

A portable, installable set of [Claude Code](https://claude.com/claude-code) skills
(slash commands). Clone it, run `./install.sh`, and the commands become available in your
Claude Code sessions — with no machine-specific paths baked in.

## Skills

| Command | What it does |
|---|---|
| `/scaffold:profile` | Set up the org/project values shared by every repo (branding, team, CI/CD, policies) once per install (`scaffold-profile.md` → profile). |
| `/scaffold:new` | Scaffold a new Databricks repo (type-driven wizard: `api` · `etl` · `job` · `agent` · `genie`). |
| `/scaffold:configure` | Fill the remaining per-repo `TODO_SET_*` placeholders a scaffolded repo ships with (`CONFIG.md` → repo). |

See [`commands/scaffold/README.md`](commands/scaffold/README.md) for the scaffold skill in
depth — the two-level config model, repo types, and the token-resolution pipeline.

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

It copies the skills into `<target>/.claude/commands/` and rewrites an install-time path
token so the slash commands find their scripts. Re-run it any time to update an install.

It then generates a fill-in **profile sheet** at `<target>/.claude/scaffold-profile.md`.
Fill in the values shared across your repos (all optional) and apply them with
`/scaffold:profile` — they get baked into every repo you scaffold. Skip the sheet with:

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
  scaffold/          profile.(md|py) + new.(md|py) + configure.(md|py)
                     + config_tokens.py + templates/
install.sh           copies commands/ into a target .claude, fixes paths, seeds the profile
scaffold-profile.{md,json}   generated per-install profile (in .claude/ root; gitignored)
```

To add a skill, drop a new folder under `commands/` following the same shape; `install.sh`
picks it up automatically.

## Design

`new.py` scaffolds every type through one path — `copytree(templates/<type>/)` then token
substitution — driven by a small `TEMPLATE_DIR` + `STANDARDS` table. Every file a repo ships
lives under `commands/scaffold/templates/` as a real file with `TPLVAR_*` / `TODO_SET_*`
tokens; the Python is pure orchestration. Adding a type is a new `templates/<type>/` dir plus
one row in the maps.

At scaffold time each token is resolved in order: an explicit `new.py` CLI arg, then the
install **profile** (`scaffold-profile.json`, org-wide values), then a `TODO_SET_*`
placeholder left for `/scaffold:configure`. Add a profile field by adding a row to `FIELDS`
in `profile.py` and mapping its key to a template token in `new.py`.
