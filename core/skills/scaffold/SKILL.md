---
name: scaffold
kind: skill
description: >
  Create a new Databricks repository from a type-driven template — ETL bundle, job
  bundle, API skeleton, agent, or Genie space — or add one aspect to a repo that already
  exists, and fill its configuration placeholders. Use when starting a new repo or
  bringing an existing one up to the org standard.
---

# Scaffold

## Entry points

- `/scaffold:new` — new repo, type-driven wizard
- `/scaffold:add` — add a single aspect to an existing repo
- `/scaffold:configure` — fill config placeholders (`CONFIG.md` → repo)
- `/scaffold:profile` — set up the shared org/project profile sheet

## Payload

- `templates/` — one directory per repo type, plus the `*_STANDARDS.md` documents
- `new.py` · `add.py` · `configure.py` · `aspects.py` · `config_tokens.py` · `profile.py`

Org-wide values (branding, team, CI/CD, cluster policies) come from the profile sheet,
which is generated per install and never committed. Everything else is per-repo.
