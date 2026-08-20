# generated/

Build output. **Committed, and never hand-edited.**

`python/build_space.py --env <env>` writes `space.<env>.json` here from `src/`.
`resources/genie.yml` deploys the file matching `${bundle.target}`.

These are committed because the CI/CD controller clones the repo fresh and runs
no project scripts — there is nothing in the pipeline that could build them. What
is in git is what deploys.

Before promoting to stg or prod, build every environment:

```bash
./run_local.sh all      # builds dev, stg and prod, then validates
```

Building only `dev` and merging leaves stg deploying the last artifact someone
happened to commit.
