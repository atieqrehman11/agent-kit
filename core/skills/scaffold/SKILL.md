---
name: scaffold
kind: skill
description: >
  Create a new Databricks repository from a type-driven template — ETL bundle, job
  bundle, API skeleton, React front end, agent, or Genie space — or add one aspect to a
  repo that already exists, and fill its configuration placeholders. Use when starting a
  new repo or bringing an existing one up to the org standard.
---

# Scaffold

## Entry points

- `{{cmd:scaffold:new}}` — new repo, type-driven wizard
- `{{cmd:scaffold:add}}` — add a single aspect to an existing repo
- `{{cmd:scaffold:configure}}` — fill config placeholders (`CONFIG.md` → repo)
- `{{cmd:scaffold:profile}}` — set up the shared org/project profile sheet

## Payload

- `templates/<type>/` — application code only, one directory per repo type
- `templates/deploy/` — how a repo deploys: bundle descriptor, resources, `run_local.sh`
- `templates/gitlab/` — the GitLab pipeline
- `gitlab/setup-group.sh` · `gitlab/setup-repo.sh` — GitLab project setup, kit tooling
  rather than repo files: they configure the GitLab project, so one copy serves every repo
- `new.py` · `add.py` · `configure.py` · `aspects.py` · `config_tokens.py` · `profile.py`

Types: `api` · `etl` · `job` · `fe` · `agent` · `genie`. `api` and `fe` are both
`resources.apps` Databricks Apps — the backend and the front end of one product, scaffolded
as two repos. `fe` is the only type that is not a Python repo. It deploys through the shared DAB
controller like the other bundle types, but ships a committed `dist/` rather than source:
the Apps build environment cannot reach the npm registry, so nothing can be built there.

Org-wide values (branding, team, CI/CD, cluster policies) come from the profile sheet,
which is never committed. Everything else is per-repo.

A profile is **scoped**: `<project>/__PROJECT_SCOPE_DIR__/scaffold-profile.md` governs
that project and beats the install-wide one in the kit data dir. On a machine serving more than one
client, give each client's tree its own — those values are what differ between clients,
and a repo scaffolded with the wrong one looks correct. Every command that reads a
profile prints which one it used before writing anything.
