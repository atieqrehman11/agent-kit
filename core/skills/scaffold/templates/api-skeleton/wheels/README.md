# wheels/

Committed dependency wheels. **Tracked in git, not ignored.**

The Databricks Apps build environment has no outbound network, so nothing can be
installed there at deploy time. Every dependency in `requirements.txt` ships as a
wheel in this directory, and `databricks.yml` names it under `sync.include` so it
reaches the workspace.

Both halves are needed. Ignoring `wheels/` and relying on the sync line alone
uploads whatever happens to be on the deploying laptop and leaves the CI/CD
controller — which clones the repo fresh — with nothing to install. That failure
shows up as a green deploy and an app that will not start.

## Refreshing them

Build for the Apps runtime, not for your laptop — the platform is Linux x86-64 on
Python 3.11, so a wheel resolved on an ARM Mac will not install there:

```bash
rm -rf wheels && mkdir wheels
pip download -r requirements.txt -d wheels \
  --platform manylinux2014_x86_64 \
  --python-version 3.11 \
  --only-binary=:all:
git add wheels
```

Re-run this whenever `requirements.txt` changes, and commit the result in the
same change — a stale `wheels/` deploys green and runs the previous versions.
