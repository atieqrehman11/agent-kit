---
name: profile
kind: command
description: >
  Set up the values that are identical across every repo a team scaffolds — doc branding,
  workspace folder, ownership, permissions, CI/CD and cluster policies. Collected once per
  scope: the whole machine, or one client's tree so another client's values cannot reach
  it. Run before the first scaffold, or when those org-wide values change.
---

# Set up the shared org/project profile

Sets up the values that are the **same across every repo** in one scope — doc branding,
workspace project folder, team/ownership, app permissions, CI/CD, and cluster policies.
`{{cmd:scaffold:new}}` reads the profile and bakes these into every new repo, so they never
appear in a repo's `CONFIG.md`. Every field is optional; anything left blank stays a
`TODO_SET_*` placeholder that `{{cmd:scaffold:configure}}` fills per repo.

**One file per scope: `scaffold-profile.md`.** You edit it, every command reads it. There
is no apply step and no second copy — save the file and the values are live.

```bash
python3 __SKILL_DIR__/profile.py \
  [--generate] \                    # (re)write the file, keeping every value in it
  [--show] \                        # report only; never creates the file
  [--scope auto|project|global] \   # which profile to act on (default: auto)
  [--project-dir <dir>]             # with --scope project: the project root
# no flag = report the profile in force, creating it if it does not exist yet
```

Unlike `{{cmd:scaffold:configure}}`, this command does not transform anything: applying a
`CONFIG.md` writes values across a whole repo tree, whereas a profile is just the file.

## Scope — global or per client

A profile has a **scope**, because a machine serves more than one client and these are
exactly the values that differ between them.

| Scope | Lives in | Governs |
|---|---|---|
| `project` | `<project>/__PROJECT_SCOPE_DIR__/` | that project and everything under it — **wins** |
| `global` | the kit data dir | everything else on the machine |

Resolution, used identically by every command that reads a profile:

```
$AGENT_KIT_PROFILE                                 an explicit file, one invocation
<dir>/__PROJECT_SCOPE_DIR__/scaffold-profile.md    nearest project profile, walking up
<kit data dir>/scaffold-profile.md                 install-wide fallback
```

**Use `--scope project` whenever the machine scaffolds for more than one client.** With
only a global profile, running `{{cmd:scaffold:new}}` inside client B's tree produces a repo
branded for client A and wired to client A's CI controller, and the repo looks correct
either way. A project profile is created gitignored — it holds CI ids, a workspace group
and team addresses, which are operator state and not the client's source.

Every command that reads a profile prints which one it used before it does any work. If
it reports `global` while a project `__PROJECT_SCOPE_DIR__/` sits above the working
directory, it says so — that is the case to fix with `--generate --scope project`.

## Flow

**Step 1 — Decide the scope.** Working inside one client's tree, and other clients exist
on this machine? Use `--scope project`. Setting up values that genuinely apply everywhere
(an output dir, a draw.io binary path)? `--scope global`. `auto` (the default) acts on
whichever profile already governs the working directory.

**Step 2 — Run it.** With no flag the script reports the profile in force and its scope,
and creates the file if that scope has none. Report the path it printed.

**Step 3 — Fill it in.** Open that `scaffold-profile.md` and set the values shared across
the scope's repos (output dir, org name, workspace project, team, developers group, prod
admin, CI controller URL + runner + project id + image, cluster policies). Read the
**Reference** table at the top of the file for what each field is and where to get it.
Leave a line blank to keep that value per-repo. Keep the keys as-is.

**Step 4 — Nothing.** Saving the file is the whole of it. Run the script again to confirm
what is now set and what is still blank.

`--generate` on an existing profile rewrites it while keeping every value — that is how a
field contributed by a newly installed skill appears in a profile older than it.

## Notes

- **Optional by design.** A blank field is not an error — it just stays a `TODO_SET_*`
  placeholder that `{{cmd:scaffold:configure}}` resolves for each repo.
- **Precedence at scaffold time:** an explicit `new.py` CLI arg wins over the profile,
  which wins over the `TODO_SET_*` placeholder.
- **Do not hand-write the file from scratch.** Generate it, then edit the values. The
  reference table and the per-field hints come from the installed skills' field
  declarations, and a hand-rolled file silently lacks whatever they added.
- **Values are plain text after the colon.** No quotes needed; a `#` preceded by a space
  starts a comment, so a value cannot itself contain " #".
- **Scopes do not merge.** The nearest profile is used whole; a project profile does not
  inherit the global one's unset fields. Whatever a project leaves blank stays a
  `TODO_SET_*` for `{{cmd:scaffold:configure}}` — which is the safe direction, since
  inheriting would quietly reintroduce another client's CI controller.
- **The org-prefix token in the installed guidelines is install-wide.** It is resolved
  once, at install time, from the global profile — a project profile's `org` reaches every
  repo `{{cmd:scaffold:new}}` generates, but not the guideline copies in the kit itself.
  (Naming that token in prose here would be pointless: the installer substitutes it in
  this file too, which is how this bullet once read "`Acme ` in the installed
  guidelines".)
- **Where values land in a scaffolded repo:** `databricks.yml` (workspace project folder,
  prod admin), the app resource (developers group), `.gitlab-ci.yml` (runner,
  controller project id, CI image, team), and the docs' brand title.
- **`output_dir` is special:** it is *not* baked into a repo and never becomes a
  `TODO_SET_*` placeholder — it only tells `new.py` where to create the repo folder.
  Resolution: `--output-dir` > `$SCAFFOLD_OUTPUT_DIR` > profile `output_dir` > current dir
  (`~` and `$VARS` are expanded).
- **Upgrading from the two-file profile.** Earlier versions applied the sheet into a
  `scaffold-profile.json` that the commands read. That file is no longer read. The first
  run after upgrading carries its values into the profile and says so; delete it once the
  profile looks right.
- **One file, every skill.** The profile is shared across the install. Other skills
  contribute their own fields (each declares them in its own `profile_fields.py`), so the
  sheet may list groups this skill never uses — e.g. an eval engine path or a diagrams
  output folder. Fill only what you need.
- **Add a new profile field?** For a scaffold field, add a row to `FIELDS` in `profile.py`
  (key, group, label, example, used-in, source) and map the key to its template token in
  `new.py` (`_PROFILE_TODO_TOKENS`, or a `TPLVAR_` assignment for tokens filled inline).
  For another skill's field, add the row to **that skill's** `profile_fields.py` instead —
  it is picked up here automatically.
