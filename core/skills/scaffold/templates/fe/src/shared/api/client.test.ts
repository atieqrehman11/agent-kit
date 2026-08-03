import { http, HttpResponse } from 'msw'
import { z } from 'zod'

import { server } from '@/test/msw'

import { ApiError, request } from './client'

const widget = z.object({ id: z.string(), count: z.number() })

describe('api client', () => {
  it('returns the parsed body on success', async () => {
    server.use(http.get('*/api/widget', () => HttpResponse.json({ id: 'w1', count: 3 })))

    await expect(request('/widget', widget)).resolves.toEqual({ id: 'w1', count: 3 })
  })

  it('turns the platform error envelope into an ApiError', async () => {
    server.use(
      http.get('*/api/widget', () =>
        HttpResponse.json(
          {
            error_code: 'RESOURCE_NOT_FOUND',
            message: 'No such widget.',
            request_id: 'req-42',
          },
          { status: 404 },
        ),
      ),
    )

    const error = await request('/widget', widget).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 404,
      code: 'RESOURCE_NOT_FOUND',
      message: 'No such widget.',
      requestId: 'req-42',
    })
  })

  it('fails loudly when the response does not match the schema', async () => {
    // The case this client exists for: the backend renamed a field, and without
    // the parse the component downstream would read `undefined` instead.
    server.use(http.get('*/api/widget', () => HttpResponse.json({ id: 'w1', total: 3 })))

    const error = await request('/widget', widget).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).code).toBe('SCHEMA_MISMATCH')
    expect((error as ApiError).message).toContain('count')
  })

  it('reports a transport failure as one error shape, not a TypeError', async () => {
    server.use(http.get('*/api/widget', () => HttpResponse.error()))

    const error = await request('/widget', widget).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).code).toBe('NETWORK_ERROR')
  })
})
