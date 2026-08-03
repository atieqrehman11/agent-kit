import { setupServer } from 'msw/node'

/** The mock HTTP layer. Tests exercise the real API client against it rather
 * than mocking the client module — a mocked client agrees with whatever the
 * test asserts, including when the client itself is wrong.
 *
 * Handlers are registered per test with `server.use(...)`; there are no default
 * handlers, so an unhandled request fails loudly (see setup.ts). */
export const server = setupServer()
