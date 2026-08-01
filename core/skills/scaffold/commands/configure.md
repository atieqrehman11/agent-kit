# Fill a repo's config placeholders (CONFIG.md → repo)

Resolves the `TODO_SET_*` placeholders a scaffolded repo ships with. Every repo created
by `/scaffold:new` gets a one-page **`CONFIG.md`** at its root listing exactly the
placeholders it still contains, grouped and annotated (label + example + which files use
it). This command drives that sheet: it can (re)generate it and it applies the filled
values across the whole repo tree by exact token replacement.

The heavy lifting is a deterministic script — do **not** hand-edit files to resolve
placeholders. Run the script.

```bash
python3 __SKILL_DIR__/configure.py \
  --repo "<path-to-repo>" \
  [--generate] \        # (re)write CONFIG.md from the repo's remaining placeholders, then exit
  [--dry-run] \         # preview the apply without writing
  [--display-name "<title>"] \   # title for a generated sheet (default: repo folder name)
  [--file "<sheet>"]    # config sheet path (default: <repo>/CONFIG.md)
```

## Flow

**Step 1 — Identify the repo.** If the user didn't name one, list the candidate scaffolded
repos in the output directory (`$SCAFFOLD_OUTPUT_DIR` or the current directory, e.g.
`ls -d */`) and ask which. Resolve to an absolute path.

**Step 2 — Make sure the sheet exists and is filled.**
- If `CONFIG.md` is missing (older repo, or it was deleted), run with `--generate` to
  create it, then tell the user to fill it and come back. Stop here.
- If it exists, read it and check whether any `TODO_SET_X:` lines have a value after the
  colon. If every line is blank, the user hasn't filled it yet — point them at it and stop.
  (Each line may carry a trailing `# hint`; the parser strips it, so a value left alongside
  its hint is read correctly.)

**Step 3 — Preview.** Run once with `--dry-run` and show the user what would be set (token
→ value, file count) and what would remain unresolved. This is the confirm gate.

**Step 4 — Apply.** On confirmation, run without `--dry-run`. Report:
- which tokens were set (and in how many files),
- which placeholders are still unresolved (blank lines the user left for later).

Re-running is safe and idempotent: the sheet is never rewritten by an apply, so its keys
survive, and only the still-present tokens get replaced next time.

Regenerating (`--generate`, and the automatic regeneration after `/scaffold:add`) **keeps any
value already typed into the sheet** and drops tokens that no longer appear anywhere in the
tree — those have already been applied. So a half-filled sheet is never lost by adding new
files to the repo.

## Notes

- **Exact-match replacement.** Values are applied by replacing the literal token
  (`TODO_SET_STG_WORKSPACE_HOST` → your value) everywhere it appears. Never rename the keys
  in `CONFIG.md`.
- **Partial fills are fine.** Leave a line blank to keep that placeholder for now; fill it
  and re-run later. The sheet only lists what is still unresolved when regenerated.
- **The sheet is not read at deploy time.** It only drives this step. Once every value is
  applied you may keep `CONFIG.md` as a record or delete it.
- **Where values land:** `databricks.yml` (workspace hosts, service principals),
  `team_config.yaml` (repo url, SP ids, policy id), `app.yml` (api runtime env: warehouse,
  chat gateway, genie), and any other file containing a matching token.
- **Add a new placeholder?** Register it in `config_tokens.py` (token → group, label,
  example) so it groups correctly in generated sheets. Unregistered tokens still appear
  under an "Other" group, so nothing is silently missed.
