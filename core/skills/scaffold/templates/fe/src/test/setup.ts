import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'

import { server } from './msw'

// `error` rather than `warn`: a request no handler covers means the test is
// hitting something it did not intend to, and a warning in a green run is a
// warning nobody reads.
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

afterEach(() => {
  cleanup()
  server.resetHandlers()
})

afterAll(() => server.close())

// jsdom implements neither, and shadcn/ui components (and any media query the
// app makes) call both. Stubbed here once rather than in each test file.
globalThis.matchMedia ??= ((query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: () => {},
  removeListener: () => {},
  addEventListener: () => {},
  removeEventListener: () => {},
  dispatchEvent: () => false,
})) as typeof globalThis.matchMedia

globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}
