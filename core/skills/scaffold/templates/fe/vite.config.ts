import path from 'node:path'
// `vitest/config` re-exports Vite's defineConfig with the `test` block typed,
// so dev, build and test configuration stay in one file.
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Dev-only: forward `/api/*` to a backend, mirroring what server.mjs does in the
// deployed App — so dev and production exercise the same same-origin path and no
// environment's URL ever reaches the browser bundle.
//
// No URL is hardcoded. Without BACKEND_API_UPSTREAM the route is not registered
// at all, and `/api` calls 404 — the honest signal that nothing is configured.
//
// A DEPLOYED Databricks App also needs BACKEND_API_TOKEN: the platform answers
// 401 before the request reaches the app. A local backend needs no token.
const BACKEND_API_UPSTREAM = process.env.BACKEND_API_UPSTREAM || ''
const BACKEND_API_TOKEN = process.env.BACKEND_API_TOKEN || ''

export default defineConfig({
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
})
