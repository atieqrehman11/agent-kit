import { z } from 'zod'

/** The one HTTP client. Every call in the app goes through it.
 *
 * Two decisions worth knowing before you add a call:
 *
 * 1. **The base is a same-origin path, never an origin.** In the deployed app
 *    `server.mjs` proxies `/api/*` to the backend; in dev the Vite proxy does.
 *    So no backend URL — and no token needed to reach it — is ever compiled into
 *    the bundle. Passing an absolute URL here defeats that, and the credential
 *    leaks with it.
 *
 * 2. **Every response is parsed with Zod.** A backend that changes its contract
 *    should surface as one typed error at this boundary, not as `undefined`
 *    three components deep, half a second after the user clicked something. */
export const API_BASE = '/api'

/** The platform error envelope (docs/API_STANDARDS.md §7). Only the fields the
 * UI actually uses are required — a stricter schema here would turn a backend
 * that omits `detail` into a client-side crash. */
const errorEnvelope = z.object({
  error_code: z.string(),
  message: z.string(),
  request_id: z.string().nullish(),
})

/** One error shape for the whole app, so every caller handles failure the same
 * way. `requestId` is what support needs to find the request in the backend's
 * logs — surface it in any error UI that a user might screenshot. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string | undefined

  constructor(status: number, code: string, message: string, requestId?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }
}

async function readError(res: Response): Promise<ApiError> {
  let body: unknown
  try {
    body = await res.json()
  } catch {
    // A non-JSON error body means something in front of the API answered — a
    // gateway, the proxy, an auth layer. Say so rather than guessing a code.
    return new ApiError(res.status, 'NON_JSON_ERROR', `HTTP ${res.status} from ${res.url}`)
  }
  const parsed = errorEnvelope.safeParse(body)
  if (!parsed.success) {
    return new ApiError(res.status, 'UNKNOWN_ERROR', `HTTP ${res.status} from ${res.url}`)
  }
  return new ApiError(
    res.status,
    parsed.data.error_code,
    parsed.data.message,
    parsed.data.request_id ?? undefined,
  )
}

export interface RequestOptions {
  method?: string
  body?: unknown
  signal?: AbortSignal
  headers?: Record<string, string>
}

/** Call the API and return a value the schema has vouched for.
 *
 * Throws `ApiError` and nothing else — including for network failures, so a
 * caller never has to tell a `TypeError` from a 500. */
export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  options: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', body, signal, headers = {} } = options

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      signal,
      headers:
        body === undefined ? headers : { 'content-type': 'application/json', ...headers },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new ApiError(0, 'NETWORK_ERROR', 'The request could not be sent.')
  }

  if (!res.ok) throw await readError(res)

  let payload: unknown
  try {
    payload = await res.json()
  } catch {
    throw new ApiError(res.status, 'INVALID_JSON', 'The response was not valid JSON.')
  }

  const parsed = schema.safeParse(payload)
  if (!parsed.success) {
    const where = parsed.error.issues
      .map((issue) => `${issue.path.join('.') || '(root)'}: ${issue.message}`)
      .join('; ')
    throw new ApiError(
      res.status,
      'SCHEMA_MISMATCH',
      `The response did not match the expected shape — ${where}`,
    )
  }
  return parsed.data
}
