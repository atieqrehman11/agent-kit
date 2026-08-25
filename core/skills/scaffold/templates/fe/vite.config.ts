import path from 'node:path'
// `vitest/config` re-exports Vite's defineConfig with the `test` block typed,
// so dev, build and test configuration stay in one file.
import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Dev-only: forward `/api/*` to a backend, mirroring what server.mjs does in the
// deployed App — so dev and production exercise the same same-origin path and no
// environment's URL ever reaches the browser bundle.
//
// No URL is hardcoded. Without BACKEND_API_UPSTREAM the route is not registered
// at all, and `/api` calls fall through to the SPA — see the warning below.
//
// A DEPLOYED Databricks App also needs BACKEND_API_TOKEN: the platform answers
// 401 before the request reaches the app. A local backend needs no token.
//
// Read through loadEnv, NOT process.env: Vite has not loaded .env files at the
// point this config is evaluated, so `process.env.BACKEND_API_UPSTREAM` is
// undefined even when .env.local sets it. The proxy then silently does not
// register and every /api call returns index.html with a 200 — which surfaces
// as a JSON parse error three layers away, not as a configuration problem. The
// empty prefix picks up unprefixed vars; a real shell export still wins.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const BACKEND_API_UPSTREAM = env.BACKEND_API_UPSTREAM || ''
  const BACKEND_API_TOKEN = env.BACKEND_API_TOKEN || ''

  // Nothing else says so: a missing upstream leaves `/api/*` to the SPA
  // fallback, which answers 200 with HTML and looks like a broken backend.
  if (!BACKEND_API_UPSTREAM && mode !== 'test') {
    console.warn(
      '\n[vite] BACKEND_API_UPSTREAM is not set — /api is NOT proxied.\n' +
        '       Every API call will return index.html and the app will show no data.\n' +
        '       Set it in .env.local (see .env.example).\n',
    )
  }

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { '@': path.resolve(__dirname, './src') },
    },
    server: {
      port: 5173,
      proxy: BACKEND_API_UPSTREAM
        ? {
            '/api': {
              target: BACKEND_API_UPSTREAM,
              changeOrigin: true,
              secure: true,
              rewrite: (p) => p.replace(/^\/api/, ''),
              configure: (proxy) => {
                proxy.on('proxyReq', (proxyReq) => {
                  if (BACKEND_API_TOKEN) {
                    proxyReq.setHeader('Authorization', `Bearer ${BACKEND_API_TOKEN}`)
                  }
                })
                // A proxied 401/404 is the other silent failure: without this the
                // browser shows a parse error and the terminal shows nothing.
                proxy.on('proxyRes', (proxyRes, req) => {
                  const status = proxyRes.statusCode ?? 0
                  if (status >= 400) {
                    console.warn(`[vite] proxy ${req.method} ${req.url} -> ${status}`)
                  }
                })
              },
            },
          }
        : undefined,
    },
    build: {
      // A soft warning during development. The hard gate is `npm run budget`,
      // which CI runs — see scripts/check-bundle-size.mjs.
      chunkSizeWarningLimit: 300,
      rollupOptions: {
        output: {
          // Stable chunk names so caching survives deploys that only touch
          // unrelated code. Each lazy feature becomes its own chunk.
          chunkFileNames: 'assets/[name]-[hash].js',
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
      css: false,
    },
  }
})
