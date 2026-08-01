# Set up the shared org/project profile (sheet → profile)

Sets up the values that are the **same across every repo** a team scaffolds — doc
branding, workspace project folder, team/ownership, app permissions, CI/CD, and cluster
policies. Collected **once per install**, not per repo. `/scaffold:new` reads the saved
profile and bakes these into every new repo, so they never appear in a repo's `CONFIG.md`.

This mirrors `/scaffold:configure`, but there is **one sheet for the whole install** and
**every field is optional** — anything left blank stays a `TODO_SET_*` placeholder that
`/scaffold:configure` fills per repo. The sheet (`scaffold-profile.md`) and the saved
profile (`scaffold-profile.json`) live in the **kit data dir**, not in the skill dir.

The heavy lifting is a deterministic script — do **not** hand-edit the saved profile.
Run the script.

```bash
python3 __SKILL_DIR__/profile.py \
  [--generate] \   # (re)write the fill-in sheet, then exit
  [--show]         # print the saved profile, then exit
# no flag = apply: parse the sheet and save to scaffold-profile.json
```

## Flow

**Step 1 — Make sure the sheet exists.** If `scaffold-profile.md` is missing, run with
`--generate` to create it (install does this for you). Existing saved values prefill the
sheet, so regenerating never loses anything.

**Step 2 — Fill it in.** Open `scaffold-profile.md` (in the kit data dir) and set the
values shared across your repos (output dir, org name, workspace project, team, developers
group, prod admin, CI controller URL + runner + project id + image, cluster policies). Leave
any line blank to keep that value per-repo. Keep the keys as-is.

**Step 3 — Apply.** Run the script with no flag. It parses the sheet and saves the filled
values to `scaffold-profile.json`. Report which values were saved and which were left
per-repo.

Re-running is safe: applying only writes `scaffold-profile.json`; the sheet is untouched,
so you can edit and re-apply any time. Newly scaffolded repos pick up the current profile.

## Notes

- **Optional by design.** A blank field is not an error — it just stays a `TODO_SET_*`
  placeholder that `/scaffold:configure` resolves for each repo.
- **Precedence at scaffold time:** an explicit `new.py` CLI arg wins over the profile,
  which wins over the `TODO_SET_*` placeholder.
- **Where values land in a scaffolded repo:** `databricks.yml` (workspace project folder,
  prod admin), the app resource (developers group), `.gitlab-ci.yml` + `team_config.yaml`
  (runner, controller project id + repo URL, CI image, team), and the docs' brand title.
- **`output_dir` is special:** it is *not* baked into a repo and never becomes a
  `TODO_SET_*` placeholder — it only tells `new.py` where to create the repo folder.
  Resolution: `--output-dir` > `$SCAFFOLD_OUTPUT_DIR` > profile `output_dir` > current dir
  (`~` and `$VARS` are expanded).
- **One sheet, every skill.** The profile is shared across the install. Other skills
  contribute their own fields (each declares them in its own `profile_fields.py`), so the
  sheet may list groups this skill never uses — e.g. an eval engine path or a diagrams
  output folder. Fill only what you need.
- **Add a new profile field?** For a scaffold field, add a row to `FIELDS` in `profile.py`
  (key, group, label, example, used-in, source) and map the key to its template token in
  `new.py` (`_PROFILE_TODO_TOKENS`, or a `TPLVAR_` assignment for tokens filled inline).
  For another skill's field, add the row to **that skill's** `profile_fields.py` instead —
  it is picked up here automatically.
