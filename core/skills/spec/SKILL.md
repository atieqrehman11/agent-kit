---
name: spec
kind: skill
description: >
  Create a numbered feature spec with its task list, and validate an existing one for
  completeness. Use when starting a new feature that needs a written spec, or when
  checking that a spec and its tasks are complete before work begins.
---

# Spec

A feature spec lives at `<specs-root>/<NNN>-<slug>/` as `spec.md` + `tasks.md`. The specs
root resolves in this order: `--specs-root`, then `$SPEC_ROOT`, then the `specs_root` key
of the spec profile, then `./specs`.

## Usage

Create the next numbered spec:

```
python3 __SKILL_DIR__/spec.py new --title "<title>"
```

Validate an existing one — deterministic gates only; anything needing judgement is your
job, not the script's:

```
python3 __SKILL_DIR__/spec.py check <NNN>-<slug>
```

## Payload

- `templates/spec.md` · `templates/tasks.md`
- `spec.py`

Columns are always looked up by header name. Users reorder columns for readability, and
position-based access then reads the wrong one and returns plausible garbage.
