// Production server for the Databricks App: serves the built SPA and proxies
// /api to the backend.
//
// Node built-ins only, on purpose. Nothing is installed when the app starts, so
// a cold start cannot fail on the npm registry — dist/ was built in CI (or by
// ./run_local.sh deploy) and deployed as an artifact.
//
// Two rules this file exists to enforce:
//
//   1. The browser calls a SAME-ORIGIN path. The backend's URL and any token
//      needed to reach it live here, in the server process, and never reach the
//      bundle. Grep dist/ — no host, no credential.
//   2. The process EXITS at startup when required configuration is missing. A
//      server that boots and then 500s on first use has turned a deploy-time
//      failure into a user-facing one.
//
// It also never buffers a proxied response, so a streamed model answer reaches
// the browser token by token rather than in one lump at the end.

import { createServer } from 'node:http'
import { createReadStream } from 'node:fs'
import { stat } from 'node:fs/promises'
import { extname, join, normalize, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Readable } from 'node:stream'

const PORT = Number(process.env.PORT || 8000)
const DIST = fileURLToPath(new URL('./dist', import.meta.url))
const INDEX = join(DIST, 'index.html')

// No trailing slash, so join-by-concatenation below has exactly one.
const UPSTREAM = (process.env.BACKEND_API_URL || '').replace(/\/+$/, '')
// sp | obo | none — see app.yml. `sp` is the default: this app calls the backend
// as its own service principal, using the credentials Databricks Apps injects
// below. `obo` (forward the signed-in user's token) is implemented and is the
// intended direction, but it is not the default until the backend authorizes
// per user — until then it would change WHO is calling without changing what
// they may do.
const AUTH_MODE = process.env.BACKEND_API_AUTH || 'sp'
const DEBUG = (process.env.LOG_LEVEL || 'info').toLowerCase() === 'debug'

// Databricks Apps injects these for the app's own service principal.
const DATABRICKS_HOST = (process.env.DATABRICKS_HOST || '').replace(/\/+$/, '')
const CLIENT_ID = process.env.DATABRICKS_CLIENT_ID || ''
const CLIENT_SECRET = process.env.DATABRICKS_CLIENT_SECRET || ''
// Local dev / CI escape hatch: a token supplied directly, no OAuth exchange.
const STATIC_TOKEN = process.env.BACKEND_API_TOKEN || ''

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
}

// Hop-by-hop headers, plus the ones the proxy must set itself. Forwarding `host`
// makes the upstream see this app's hostname and mis-route or reject.
const STRIP = new Set([
  'host',
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
  'authorization',
  'content-length',
  'x-forwarded-access-token',
])

const log = (...args) => console.log('[server]', ...args)
const debug = (...args) => DEBUG && console.log('[server]', ...args)

// ─── Startup checks ───────────────────────────────────────────────────────────

async function preflight() {
  const problems = []

  try {
    await stat(INDEX)
  } catch {
    problems.push(
      `dist/index.html is missing — the app was deployed without a build. Run \`npm ci && npm run build\` before \`databricks bundle deploy\` (./run_local.sh deploy does both).`,
    )
  }

  // A placeholder left unfilled is not "no backend configured", it is a repo
  // that was deployed before {{cmd:scaffold:configure}} ran. Fail loudly.
  if (UPSTREAM.includes('TODO_SET_')) {
    problems.push(
      `BACKEND_API_URL is still the placeholder ${UPSTREAM} — fill CONFIG.md and run {{cmd:scaffold:configure}}, or clear the value in app.yml to run with no backend.`,
    )
  }

  if (!['obo', 'sp', 'none'].includes(AUTH_MODE)) {
    problems.push(`BACKEND_API_AUTH must be one of obo | sp | none, got "${AUTH_MODE}"`)
  }

  // Checked here rather than on the first request: a missing credential is a
  // deploy-time fault, and discovering it as a 502 in front of a user is the
  // failure this whole preflight exists to prevent.
  if (UPSTREAM && AUTH_MODE === 'sp' && !STATIC_TOKEN) {
    const missing = [
      !CLIENT_ID && 'DATABRICKS_CLIENT_ID',
      !CLIENT_SECRET && 'DATABRICKS_CLIENT_SECRET',
      !DATABRICKS_HOST && 'DATABRICKS_HOST',
    ].filter(Boolean)
    if (missing.length) {
      problems.push(
        `BACKEND_API_AUTH=sp needs ${missing.join(' + ')} — Databricks Apps injects all three, ` +
          `so an absence here usually means this is running outside an App. For a local run, ` +
          `set BACKEND_API_TOKEN instead and no OAuth exchange happens.`,
      )
    }
  }

  if (problems.length) {
    for (const p of problems) console.error(`ERROR: ${p}`)
    process.exit(1)
  }
}

// ─── Upstream auth ────────────────────────────────────────────────────────────

let cached = { token: '', expiresAt: 0 }

// Client-credentials token for this app's own service principal. Cached until a
// minute before expiry — one exchange per hour, not one per request.
async function servicePrincipalToken() {
  const now = Date.now()
  if (cached.token && now < cached.expiresAt) return cached.token

  const res = await fetch(`${DATABRICKS_HOST}/oidc/v1/token`, {
    method: 'POST',
    headers: {
      'content-type': 'application/x-www-form-urlencoded',
      authorization: `Basic ${Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString('base64')}`,
    },
    body: 'grant_type=client_credentials&scope=all-apis',
  })
  if (!res.ok) {
    throw new Error(`token exchange failed: ${res.status} ${await res.text()}`)
  }
  const body = await res.json()
  cached = {
    token: body.access_token,
    expiresAt: now + Math.max(0, (body.expires_in || 3600) - 60) * 1000,
  }
  return cached.token
}

async function authorization(req) {
  if (AUTH_MODE === 'none') return ''

  if (AUTH_MODE === 'obo') {
    // The future path: the backend sees the signed-in person. Databricks Apps
    // injects this header only when the app declares user_api_scopes — absent
    // (local dev, or scopes not requested) fall back to a static token rather
    // than silently calling as nobody, which reads as an auth bug at the
    // backend and is really a configuration one here.
    const forwarded = req.headers['x-forwarded-access-token']
    if (forwarded) return `Bearer ${forwarded}`
    return STATIC_TOKEN ? `Bearer ${STATIC_TOKEN}` : ''
  }

  // sp — the default. A token supplied directly wins, so a local run needs no
  // client credentials; otherwise exchange the app's own id + secret.
  if (STATIC_TOKEN) return `Bearer ${STATIC_TOKEN}`
  return `Bearer ${await servicePrincipalToken()}`
}

// ─── /api proxy ───────────────────────────────────────────────────────────────

async function proxy(req, res, url) {
  if (!UPSTREAM) {
    // Same behaviour as the Vite dev proxy with no BACKEND_API_UPSTREAM set: the
    // route does not exist. A 404 says "nothing is wired" — a 502 would say "the
    // backend is down", which is a different and wrong diagnosis.
    return send(res, 404, 'no backend configured\n')
  }

  const target = UPSTREAM + url.pathname.slice('/api'.length) + url.search
  const headers = {}
  for (const [k, v] of Object.entries(req.headers)) {
    if (!STRIP.has(k.toLowerCase()) && v !== undefined) headers[k] = v
  }
  const auth = await authorization(req)
  if (auth) headers.authorization = auth

  const hasBody = req.method !== 'GET' && req.method !== 'HEAD'
  const upstream = await fetch(target, {
    method: req.method,
    headers,
    body: hasBody ? req : undefined,
    duplex: hasBody ? 'half' : undefined,
    redirect: 'manual',
  })

  debug(`${req.method} ${url.pathname} -> ${upstream.status}`)

  const out = {}
  upstream.headers.forEach((value, key) => {
    if (key !== 'content-encoding' && key !== 'transfer-encoding') out[key] = value
  })
  res.writeHead(upstream.status, out)

  if (!upstream.body) return res.end()
  // Piped, never collected: a streamed response must reach the browser as it
  // arrives. Buffering here is invisible in tests and obvious to a user.
  Readable.fromWeb(upstream.body).pipe(res)
}

// ─── Static ───────────────────────────────────────────────────────────────────

function send(res, status, body, headers = {}) {
  res.writeHead(status, { 'content-type': 'text/plain; charset=utf-8', ...headers })
  res.end(body)
}

// Resolve a URL path inside dist/, or null if it escapes. normalize() collapses
// `..` before the prefix test, so `/assets/../../etc/passwd` cannot get out.
function resolveFile(pathname) {
  let decoded
  try {
    decoded = decodeURIComponent(pathname)
  } catch {
    return null // malformed percent-encoding — not a file we own
  }
  const candidate = normalize(join(DIST, decoded))
  if (candidate !== DIST && !candidate.startsWith(DIST + sep)) return null
  return candidate
}

async function serveFile(res, file, { immutable = false } = {}) {
  const type = TYPES[extname(file).toLowerCase()] || 'application/octet-stream'
  const info = await stat(file)
  res.writeHead(200, {
    'content-type': type,
    'content-length': info.size,
    // Hashed asset filenames change when their content changes, so they can be
    // cached forever. index.html must never be — it is what points at the new
    // hashes, and a cached one pins the browser to the previous deploy.
    'cache-control': immutable
      ? 'public, max-age=31536000, immutable'
      : 'no-cache, must-revalidate',
    'x-content-type-options': 'nosniff',
  })
  createReadStream(file).pipe(res)
}

async function serveStatic(req, res, url) {
  const file = resolveFile(url.pathname)
  if (file) {
    try {
      const info = await stat(file)
      if (info.isFile()) {
        return await serveFile(res, file, { immutable: url.pathname.startsWith('/assets/') })
      }
    } catch {
      // Not a file — fall through to the SPA entry point below.
    }
  }
  // Client-side routing: any unknown path is a route the app owns, so it gets
  // index.html and React Router decides whether it is a page or a 404.
  return await serveFile(res, INDEX)
}

// ─── Server ───────────────────────────────────────────────────────────────────

const server = createServer((req, res) => {
  const url = new URL(req.url || '/', 'http://localhost')

  const handler =
    url.pathname === '/api' || url.pathname.startsWith('/api/')
      ? proxy(req, res, url)
      : serveStatic(req, res, url)

  handler.catch((err) => {
    console.error('[server] unhandled', err)
    if (!res.headersSent) send(res, 502, 'upstream error\n')
    else res.end()
  })
})

await preflight()

server.listen(PORT, () => {
  log(`listening on :${PORT}`)
  log(`backend: ${UPSTREAM || '(none — /api returns 404)'} auth=${AUTH_MODE}`)
})
