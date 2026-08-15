---
name: add
kind: command
description: >
  Add one slice of the scaffold — the CI/CD pipeline, or the use case API surface — to a
  repo that already exists, including
  repos the scaffold never created. Use to bring an existing repo up to the org standard
  without regenerating it.
arguments: "[aspect and target repo; prompted if omitted]"
---

# Add one aspect of the scaffold to an existing repo

`{{cmd:scaffold:new}}` creates a whole repo. **This adds one slice to a repo that already exists** —
including repos the scaffold never created. Two aspects are choosable:

| Aspect | What the repo gains | Repo types |
|---|---|---|
| `deploy` | How the repo deploys, independent of CI provider: `databricks.yml` + `resources/` + `run_local.sh` + `team_config.yaml` + `run_resources.yml` + `.bundleignore`. `fe` ships a committed `dist/` and a sync block that keeps `package.json` out of the app root. `genie`/`agent` are not bundles: they get `run_local.sh` + `src/validate.py` + `src/deploy.py` and no descriptor. A `job` repo also gets `config/{DEV,STG,PROD}/task_config.yaml`. | `api` `etl` `job` `fe` `genie` `agent` |
| `gitlab` | The GitLab pipeline: `.gitlab-ci.yml`. Bundle types trigger the shared DAB controller on merge to `stg`/`prod`; `genie`/`agent` validate their declaration, then run their own deploy script. The GitLab project setup it needs is `gitlab/setup-group.sh` (once per group) and `gitlab/setup-repo.sh` (per repo) — kit tooling, not repo files. | `api` `etl` `job` `fe` `genie` `agent` |
| `api` | The use case API surface: `routers/platform.py` + `config.py` — `GET /v1/health` and `GET /v1/info`, the two endpoints every use case API must expose (API_STANDARDS §3–4). | `api` |

**Not choices** — these come with any add, wherever they are missing, and are never asked
about: the **`.gitignore`** for the repo's type (Node on an `fe` repo, Python / Databricks
everywhere else), and a regenerated **`CONFIG.md`** (which keeps every value already filled
in). Standards docs (`docs/*_STANDARDS.md`) ship with `{{cmd:scaffold:new}}` per repo
type. Evaluation is its own command — **`{{cmd:eval:new}}`** — because the spec belongs to the use
case, not the scaffold.

`all` is not a third aspect: it means **bring this repo up to what `{{cmd:scaffold:new}}` would have
produced for its type** — that type's standard set, minus what is already there. An aspect
valid for the type but outside its standard set (the `api` surface, which a scaffolded `api`
repo already has) is shown as *not in the standard set* and stays opt-in by name.

## What this command guarantees

The target is someone's working repo, so:

- **Only the files the chosen aspect owns are written.** Nothing else is rewritten — in
  particular there is no tree-wide token substitution, unlike `{{cmd:scaffold:new}}`.
- **An existing file is skipped and reported, never silently replaced.** With `--force` the
  previous content is kept beside it as `<name>.bak`.
- **`--dry-run` prints the exact plan and writes nothing.**
- Some things a file copy provably cannot do (editing the repo's own `databricks.yml` or
  `app.py`). Those are printed as **manual wiring** steps — relay them; do not claim the
  aspect is finished without them.

## Wizard

Run this as an interactive wizard using the **`AskUserQuestion`** tool — every field, no
inline text prompts. Batch questions onto one screen (max four per screen). Free-text values
are captured through the auto-added **"Other"** option, so a free-text field still needs two
example options. Skip any question `{{args}}` already answers.

**Step 0 — Find the repo, then detect (no question yet).** Resolve the repo path from
`{{args}}`, the current directory, or the profile's `output_dir`. Then run the detector and
**read its output before asking anything**:

```bash
python3 __SKILL_DIR__/add.py --repo "<repo>" --detect
```

It prints the repo's type (and the evidence for it), the bundle name/uuid it found, and each
aspect's status — `PRESENT` / `PARTIAL` / `MISSING` / `N/A` — plus the exact file list for
anything missing. This is what makes the picker honest: **offer only what the repo is actually
missing.** If it cannot tell the type, ask for it (`api` · `etl` · `job` · `fe` · `genie` · `agent`)
rather than guessing.

**Step 1 — One form (`AskUserQuestion`, one screen).**

- **Aspect** — the `MISSING` / `PARTIAL` aspects for this repo, each labelled with what it
  adds. With a single candidate this is a plain confirm; with both, use `multiSelect: true`.
  Never offer an `N/A` or `PRESENT` aspect; if the user asks for a `PRESENT` one anyway, tell
  them it is already there and that replacing it needs `--force` (which backs the old file up).
- **Existing files** — only ask when the chosen aspects hit files that already exist
  (`PARTIAL`): *keep what's there* (default) vs *replace, keeping `.bak` copies* (`--force`).

Do **not** ask about `.gitignore` or `CONFIG.md` — they are handled automatically.

**Step 2 — Confirm (`AskUserQuestion`, one screen).** Echo the repo path, the resolved type,
the chosen aspects and the exact file list from `--detect`, then a single **Proceed / Cancel**.
Prefer showing a `--dry-run` first when the repo is not a fresh scaffold.

## Run

```bash
python3 __SKILL_DIR__/add.py \
  --repo "<path to the existing repo>" \
  --aspect <deploy|gitlab|api|all> \
  [--aspect <the other>] \              # repeatable
  [--type <api|etl|job|fe|genie|agent>] \  # only if detection failed or is wrong
  [--force] [--dry-run] [--no-config-sheet]
```

Everything else is inferred, in the same precedence order `{{cmd:scaffold:new}}` uses — **CLI flag >
the repo's own files > the install profile > a `TODO_SET_*` placeholder**:

- **type** — from `genie-space/space.yml`, `supervisor/supervisor.yml`, a `package.json`
  beside a `vite.config.*` (`fe` — checked before the resource scan, since a front end is
  also an `apps` resource and `.app.yml` alone cannot tell it from an `api` repo),
  `resources/*.{app,pipeline,job}.yml`, an inline `resources: apps:|pipelines:|jobs:` in
  `databricks.yml`, `app.yml`/`app.yaml`/`app.py`, `pipeline/`, then the repo-name suffix.
- **bundle name + uuid** — read from the repo's existing `databricks.yml`, so
  `team_config.yaml` and `BUNDLE_TAG` agree with the bundle that is already deployed. When
  the repo has no bundle file, a name and uuid are generated **and reported as a heads-up** —
  the same uuid must then go into `databricks.yml`, and must never change after the first deploy.
- **slug** — from the repo folder name (`ai-`/`ai-prototype-` prefix and `-<type>` suffix stripped).
- **team, runner, controller id, org, policies** — from the shared install profile.
- everything left over — a `TODO_SET_*` placeholder listed in `CONFIG.md`.

Optional overrides, all skippable: `--slug`, `--display-name`, `--description`, `--catalog`,
`--table-prefix`, `--team-name`, `--team-email`, `--gitlab-runner`,
`--controller-project-id`, `--data-sensitivity`.

`CONFIG.md` is regenerated after every add (suppress with `--no-config-sheet`), and
**values already typed into it are preserved** — adding an aspect never discards a
half-filled sheet, it only appends the placeholders the new files brought in.

## After adding

- Report the files written, the files **skipped** because they already existed, and every
  **manual wiring** step the script printed. An aspect with unfinished wiring is not done.
- Tell the user to fill the outstanding `CONFIG.md` placeholders and run **`{{cmd:scaffold:configure}}`**.
- Recommend reviewing the change as a diff (`git status` / `git diff`) before committing —
  this command deliberately writes into a live repo.

## Example

```
{{cmd:scaffold:add}}
→ (detect) ai-cable-health-job · type job (from resources/job.job.yml) · bundle cable_health_job
           deploy MISSING · gitlab MISSING · api N/A · (auto) gitignore, config-sheet
→ [picker] Add the CI/CD pipeline?   Proceed / Cancel
✓ Proceed → add.py --repo <path> --aspect deploy --aspect gitlab
   added .gitlab-ci.yml, team_config.yaml, .bundleignore, run_resources.yml,
         config/{DEV,STG,PROD}/task_config.yaml, .gitignore
   CONFIG.md — 20 placeholders outstanding → fill it, then {{cmd:scaffold:configure}}
   wiring: set CONTROLLER_TRIGGER_TOKEN in GitLab CI/CD variables; confirm BUNDLE_TAG
           matches bundle.name in databricks.yml; add config_dir + policy_id variables
           to databricks.yml per target
```
