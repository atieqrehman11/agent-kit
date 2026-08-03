# TPLVAR_DISPLAY_NAME

TPLVAR_DESCRIPTION

A React front end deployed as a **Databricks App**. The app resource is
`resources.apps` in a DAB bundle, exactly like the `api` type — the difference is
that what gets deployed is a *build artifact*, so the build has to happen before
every deploy.

Standards: [`docs/REACT_STANDARDS.md`](docs/REACT_STANDARDS.md). Audit list:
[`docs/REACT_STANDARDS_CONFORMANCE.md`](docs/REACT_STANDARDS_CONFORMANCE.md). Read the first, walk the second
before opening a merge request.

## Getting started

```bash
nvm use                 # Node 20+ (see .nvmrc)
npm run setup           # npm install + vendors the shadcn/ui components into src/shared/ui/
npm run dev             # http://localhost:5173
```

`npm run setup` is `npm install` followed by `npm run ui:init`. The second step writes the
shadcn/ui components into `src/shared/ui/` — they are **vendored, not a dependency**, which
is why that folder is excluded from linting and formatting. Re-run `ui:init` to add more.

To point the dev server at a backend:

```bash
BACKEND_API_UPSTREAM=https://<api-host> npm run dev
# a deployed Databricks App also needs a token, since the platform answers 401
# before the request reaches the app:
BACKEND_API_UPSTREAM=https://<api-host> BACKEND_API_TOKEN=$(databricks auth token --host <host> | jq -r .access_token) npm run dev
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
app.yml          Databricks App runtime spec — command + env
databricks.yml   the bundle; resources/fe.app.yml declares the app
bundle.sh        local dev-loop deploy (build → validate → deploy → run)
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

## Verify

```bash
npm run verify   # format:check → lint → typecheck → test → build → budget
```

That is exactly what CI runs and what `./bundle.sh` runs before it deploys anything. Two
parts of it are load-bearing:

- **a11y findings are errors.** `eslint-plugin-jsx-a11y` is wired as `error`, not `warn` — a
  rule nobody's build fails on is a preference, not a standard.
- **the bundle budget fails the build.** `scripts/check-bundle-size.mjs` measures gzipped
  JS + CSS against a fixed ceiling. Raise it in a commit that says why; front-end bundles only
  ever grow, one reasonable-looking dependency at a time.

## How it is served

The browser calls the **same-origin** path `/api/*`. Nothing else. `server.mjs` proxies that
to `BACKEND_API_URL`, so the backend's host — and the credential needed to reach it — exist
only in the server process and never in `dist/`. Grep the build output if you want to check;
`VITE_*` values are inlined at build time and readable by anyone with the page.

`server.mjs` has **no dependencies** — Node built-ins only. Nothing is installed when the app
starts, so a cold start cannot fail on the npm registry. That is also what makes
`.bundleignore` able to exclude `node_modules/` and `src/`: the deployed app is `dist/` +
`server.mjs` + `app.yml` and nothing else. Add a runtime dependency and that trade changes —
make it deliberately.

The backend API is the **only** thing this front end calls. Not Databricks SQL, not a model
endpoint, not a second service — everything the UI needs comes through `/api`. That is what
makes one proxy and one auth decision enough.

The proxy authenticates per `BACKEND_API_AUTH` in `app.yml`:

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
a `TODO_SET_` placeholder, or if `sp` mode is on without the credentials to use it. A server
that boots and then 502s on first use has turned a deploy-time failure into a user-facing one.

## Deploy

**Local dev loop:**

```bash
./bundle.sh          # npm ci → verify → build → bundle validate/deploy/run → apps get
```

Deploys to the **dev** workspace only, and refuses any other target.

**stg / prod:** merge to the `stg` or `prod` branch and run the manual job in
`.gitlab-ci.yml`. That job builds and then runs `databricks bundle deploy` itself.

> **Why this repo does not use the shared DAB controller.** The controller deploys from a git
> checkout and runs no Node build, so it would deploy a repo whose `dist/` does not exist —
> and `dist/` is a build artifact that must not be committed. Building and deploying therefore
> have to happen in the same job, which is why this pipeline needs its own `DATABRICKS_TOKEN`
> (masked, scoped to the `stg` and `prod` branches **separately**) instead of a controller
> trigger token. If your controller gains a Node build stage, swap the deploy jobs for the
> controller-trigger form the other bundle types use; nothing else in the repo changes.

The workspace host is **not** a CI variable — it comes from the matching target in
`databricks.yml`, so there is one answer to "which workspace is stg".

## Configuration

Every deferred value ships as a `TODO_SET_*` placeholder listed in `CONFIG.md`. Fill that
sheet and apply it in one pass with `{{cmd:scaffold:configure}}`. The one specific to this
repo type is `TODO_SET_BACKEND_API_URL` in `app.yml` — the use case API this front end
proxies to.

**The brand accent is not a placeholder.** `src/styles/globals.css` ships a working neutral
indigo, and light and dark need *different* lightness values for the same hue, so no single
substituted token could set both. Change the two `--primary` values together and re-check
contrast.

`globals.css` is the only file that knows brand colours: raw values are CSS custom
properties declared in **both** themes, republished to Tailwind with `@theme inline`. A
literal colour in a component is a bug. Contrast is checked in both themes — dark is where
WCAG AA quietly fails.
