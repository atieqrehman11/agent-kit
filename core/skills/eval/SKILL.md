---
name: eval
kind: skill
description: >
  Scaffold an evaluation spec into the repository that owns the use case, wired to a
  deployed agent, an HTTP backend, or an OpenAI-compatible endpoint. Use when a use
  case needs an eval suite, or when asked to add or change evaluation for one.
---

# Eval

The eval **engine** is shared and generic; each use case owns its own `evaluation/`
folder. Never copy the harness into a use-case repo, and never add use-case-specific
code to the engine.

## Entry points

- `/eval:new` — create `evaluation/` (spec + question CSVs + runner) in the owning repo

## Payload

- `templates/` — `spec.py`, `run.sh`, `questions.csv`, `benchmark.csv`, README

Nothing is pre-defaulted: the spec dictates the target, the adapter and the judges. The
generated runner locates the engine by env var, then profile, then a sibling checkout.
