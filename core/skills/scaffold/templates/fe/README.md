# TPLVAR_APP_NAME

TPLVAR_DESCRIPTION

---

## Stack

Vite · React 19 · TypeScript (strict) · React Router · TanStack Query ·
Tailwind CSS v4 · shadcn/ui (vendored into `src/shared/ui/`) · lucide-react.

The deployment server ([server.mjs](server.mjs)) is Node with **zero
dependencies** — `node:http`, `node:fs` and global `fetch`. The whole repo is
one language.

## Getting started

```bash
nvm use                 # Node 22+ (see .nvmrc)
pnpm install            # dependencies
pnpm run ui:init        # vendors the shadcn/ui components into src/shared/ui/
pnpm run dev            # http://localhost:5173
```

pnpm, not npm: `pnpm-lock.yaml` is the lockfile and Databricks Apps picks its package
manager from it.

`ui:init` writes the shadcn/ui components into `src/shared/ui/` — they are **vendored, not a
dependency**, which is why that folder is excluded from linting and formatting. Re-run it to
add more.

To point the dev server at a backend:

```bash
BACKEND_API_UPSTREAM=https://<api-host> pnpm run dev
# a deployed Databricks App also needs a token, since the platform answers 401
# before the request reaches the app:
BACKEND_API_UPSTREAM=https://<api-host> BACKEND_API_TOKEN=$(databricks auth token --host <host> | jq -r .access_token) pnpm run dev
```

Without `BACKEND_API_UPSTREAM` the `/api` route is not registered at all and those calls
404 — the honest signal that nothing is wired, rather than a confusing connection error.

## Layout

```
src/
  app/           the shell — registry, routes, providers, error boundary, 404
  features/      one folder per feature; each is lazy-loaded and self-contained
  shared/        api client, lib/, ui/ (vendored shadcn), hooks/
  styles/        globals.css — the ONLY file that knows brand colours
  test/          vitest setup + the MSW server
server.mjs       production server: serves dist/, proxies /api  (no dependencies)
databricks.yml   the bundle — one set of per-environment values per target
resources/fe.app.yml   declares the app AND its runtime spec (command + env)
                 There is deliberately no root app.yml: it would upload verbatim
                 and could not hold a per-environment value.
.env.example     the names to copy into .env.local for local development
run_local.sh     local dev loop and dev deploy (build → validate → deploy → run)
```

### Adding a feature

One entry in `src/app/registry.ts`. Navigation and routing are both derived from it, so
**no shell file is edited** — if you find yourself editing `shell.tsx` or `routes.tsx` to add
a page, something has stopped reading the registry and the next feature will cost the same
again. `src/app/registry.test.tsx` asserts that derivation.

A feature with `status: 'soon'` appears in the nav as unavailable and registers no route; its
URL reaches the 404 surface like any other unknown path.

Features may not import one another — `no-restricted-imports` enforces it. They talk through
`@/shared` and `@/app`, and reach their own files by relative path.

### Styling

Tailwind v4 with the design tokens declared in `src/styles/globals.css` — the only
file that knows brand colours. Reach for the existing tokens rather than literal
values, and use `--shadow-soft` plus a fill for separation instead of borders.

## Configuration

One rule covers most of it: **no environment's URL is in this repo's code.** The browser
calls the same-origin `/api` path and something proxies it — `server.mjs` when deployed,
the Vite dev proxy locally. Per-target values are bundle variables in `databricks.yml`,
read by the server at runtime, so repointing an environment is a variable edit and a
redeploy with no rebuild.

- There is **no build-time knob.** `src/shared/api/client.ts` hardcodes `/api`, so no
  environment URL can be baked into the shipped JavaScript.
- Runtime, per target — `backend_api_url`, `backend_api_auth` and `log_level` in
  `databricks.yml`, turned into the App's env by `resources/fe.app.yml`.
- Local development — `.env.local`, copied from `.env.example`.

## Verify

```bash
pnpm run verify   # format:check → lint → typecheck → test → build → budget
```

`./run_local.sh deploy` runs it before deploying anything, and `SKIP_VERIFY=1` bypasses it.
**CI runs no Node job at all**, so that local run is the only place a broken build is caught
before it reaches a workspace — a deploy that skips verify has nothing behind it. Two parts of
it are load-bearing:

- **a11y findings are errors.** `eslint-plugin-jsx-a11y` is wired as `error`, not `warn` — a
  rule nobody's build fails on is a preference, not a standard.
- **the bundle budget fails the build.** `scripts/check-bundle-size.mjs` measures gzipped
  JS + CSS against a fixed ceiling. Raise it in a commit that says why; front-end bundles only
  ever grow, one reasonable-looking dependency at a time.

## Backend

The browser calls the **same-origin** path `/api/*`. Nothing else. `server.mjs` proxies that
to `BACKEND_API_URL`, so the backend's host — and the credential needed to reach it — exist
only in the server process and never in `dist/`. Grep the build output if you want to check;
`VITE_*` values are inlined at build time and readable by anyone with the page.

`server.mjs` has **no dependencies** — Node built-ins only. Nothing is installed when the app
starts, so a cold start cannot fail on the npm registry. That is also what makes
`.bundleignore` able to exclude `node_modules/` and `src/`: the deployed app is `dist/` +
`server.mjs` + the app spec and nothing else. Add a runtime dependency and that trade changes —
make it deliberately.

The backend API is the **only** thing this front end calls. Not Databricks SQL, not a model
endpoint, not a second service — everything the UI needs comes through `/api`. That is what
makes one proxy and one auth decision enough.

The proxy authenticates per `BACKEND_API_AUTH`, set in the `env` block of
`resources/fe.app.yml`:

| Mode | What the backend sees | Needs |
|---|---|---|
| `sp` (default) | this app's own service principal | nothing to configure — Databricks Apps injects `DATABRICKS_CLIENT_ID` + `DATABRICKS_CLIENT_SECRET`, and `server.mjs` exchanges them for a token and caches it until a minute before expiry. The API must grant that principal `CAN_USE` in the api repo's app resource, or every call is 401 |
| `obo` | the signed-in user | uncomment `user_api_scopes` in `resources/fe.app.yml` — requesting a scope is what makes the platform inject `X-Forwarded-Access-Token`, which the proxy already forwards |
| `none` | an anonymous caller | nothing; the backend is public or authenticates some other way |

**`obo` is where this is going, not where it is.** It is implemented and switching to it is a
one-word change plus uncommenting the scopes — but do it only once the backend authorizes
*per user*. Forwarding a user token to a backend that still authorizes by service principal
changes who is calling without changing what they are allowed to do, which looks like
progress and is not.

**No secret lives in this repo.** In `sp` mode there is nothing to store: the credentials
arrive as environment variables the platform sets. Locally, `BACKEND_API_TOKEN` short-circuits
the exchange so a laptop run needs no client secret either.

The server **exits at startup** if `dist/index.html` is missing, if `BACKEND_API_URL` is still
unset, or if `sp` mode is on without the credentials to use it. A server
that boots and then 502s on first use has turned a deploy-time failure into a user-facing one.

## Deployment

### Dev — local loop

```bash
./run_local.sh deploy          # pnpm install → verify → build → bundle validate/deploy/run
```

Deploys to the **dev** workspace only, and refuses any other target.

### stg / prod — the CI/CD controller

Merge to the `stg` branch (automatic) or `prod` (manual — play in
Build → Pipelines). This repo's pipeline never deploys; it validates the bundle config and
triggers the shared DAB CI/CD controller, exactly like every other bundle type. There is no
`DATABRICKS_TOKEN` in CI — set `CONTROLLER_TRIGGER_TOKEN` (protected + masked) instead, and
keep `stg` and `prod` protected or the trigger posts an empty token and still goes green.

> **`dist/` is committed, and that is what makes this work.** The controller deploys from a
> fresh clone and runs no Node build, and the Apps build environment cannot resolve
> `registry.npmjs.org` (`getaddrinfo EAI_AGAIN`), so nothing can install or build on the
> platform either. The built artifact therefore has to be in the repo. **Rebuild and commit
> `dist/` whenever `src/` changes**, or stg serves a stale bundle — `run_local.sh deploy`
> builds it for you, but only committing it gets it to stg. `package.json` is also kept out
> of the app root on purpose: its presence makes the Apps platform attempt an install.

The workspace host is **not** a CI variable — it comes from the matching target in
`databricks.yml`, so there is one answer to "which workspace is stg".

### What the server reads

Everything comes from the environment; the server holds no URLs of its own and
**exits at startup** if `BACKEND_API_URL` is unset, so a misconfigured deploy is
loud in the App logs instead of looking healthy and answering nothing.

There is **no `app.yaml`**. A synced one is uploaded verbatim — DAB does not
interpolate it — so it cannot hold a per-environment value. The App's `command`
and `env` are declared in `resources/fe.app.yml` under `config:`, fed by bundle
variables each target can override.

| Env var             | Set in                     | Default | Purpose                             |
| ------------------- | -------------------------- | ------- | ----------------------------------- |
| `BACKEND_API_URL`   | `${var.backend_api_url}`   | —       | Backend to proxy to (**required**)  |
| `BACKEND_API_AUTH`  | `${var.backend_api_auth}`  | `sp`    | `sp` \| `obo` \| `none`             |
| `LOG_LEVEL`         | `${var.log_level}`         | `info`  | `debug` logs one line per proxy hop |
| `PORT`              | platform                   | `8000`  | Listen port                         |

## Related repos

| Repo | Relationship |
|---|---|
| `TPLVAR_SLUG-api` | Upstream. The backend this front end proxies to; its App URL is the `backend_api_url` variable per target, and it must grant this app's service principal `CAN_USE`. |
