import ky, { HTTPError } from 'ky'

/**
 * ky extends `HTTPError` with a structured error code pulled from the
 * backend's `RESTAPIError` body. Callers can test for well-known codes
 * (e.g. `database_unavailable`) without string-matching on `err.message`.
 */
export interface ApiErrorPayload {
  error: string
  error_description: string
}

export function getApiErrorCode(err: unknown): string | null {
  if (err instanceof HTTPError) {
    const code = (err as HTTPError & { apiErrorCode?: string }).apiErrorCode
    return code ?? null
  }
  return null
}

const api = ky.create({
  prefix: import.meta.env.VITE_API_BASE_URL || '/',
  timeout: 120000,
  hooks: {
    beforeRequest: [
      ({ request }) => {
        const apiKey = import.meta.env.VITE_API_KEY
        if (apiKey) {
          request.headers.set('X-API-Key', apiKey)
        }
      },
    ],
    beforeError: [
      ({ error }) => {
        if (!(error instanceof HTTPError)) return error
        const { response } = error

        // ky pre-parses the response body into `error.data` before invoking
        // this hook, and the underlying body stream is already consumed —
        // so `response.json()` / `response.clone().json()` won't work here.
        // Lift the structured `{ error, error_description }` out of `data`
        // so callers that surface `err.message` get an actionable string
        // instead of ky's default "Request failed with status code …".
        const data = (error.data ?? null) as Partial<ApiErrorPayload> | null
        if (data && typeof data.error_description === 'string' && data.error_description) {
          error.message = data.error_description
          if (typeof data.error === 'string') {
            ;(error as HTTPError & { apiErrorCode?: string }).apiErrorCode = data.error
          }
          return error
        }

        if (response.status >= 500) {
          error.message =
            response.status === 503
              ? `A required service is unavailable (HTTP 503). Check the gemini-rest-api and gemini-db containers.`
              : `Server error (HTTP ${response.status}). Check the gemini-rest-api logs for details.`
        } else if (response.status >= 400 && response.status !== 404) {
          error.message = `Request rejected (HTTP ${response.status} ${response.statusText || ''}).`.trim()
        }
        return error
      },
    ],
  },
})

export async function get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const searchParams = params
    ? Object.fromEntries(Object.entries(params).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)]))
    : undefined
  return api.get(path, { searchParams }).json<T>()
}

export async function getOrEmpty<T>(path: string, params?: Record<string, unknown>): Promise<T[]> {
  try {
    return await get<T[]>(path, params)
  } catch (err) {
    if (err instanceof Error && 'response' in err) {
      const response = (err as { response: Response }).response
      if (response.status === 404) return []
    }
    throw err
  }
}

export async function post<T>(path: string, data?: unknown): Promise<T> {
  return api.post(path, { json: data }).json<T>()
}

export async function patch<T>(path: string, data?: unknown): Promise<T> {
  return api.patch(path, { json: data }).json<T>()
}

export async function del(path: string, opts?: { signal?: AbortSignal }): Promise<void> {
  await api.delete(path, { signal: opts?.signal })
}

export async function getBlob(path: string): Promise<Blob> {
  return api.get(path).blob()
}

export async function postBlob(path: string, data?: unknown): Promise<Blob> {
  return api.post(path, { json: data }).blob()
}

export async function postForm<T>(path: string, formData: FormData): Promise<T> {
  return api.post(path, { body: formData }).json<T>()
}

export async function getNdjson<T>(path: string, params?: Record<string, unknown>): Promise<T[]> {
  const searchParams = params
    ? Object.fromEntries(Object.entries(params).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)]))
    : undefined
  const response = await api.get(path, { searchParams })
  const text = await response.text()
  if (!text.trim()) return []
  return text.trim().split('\n').map((line) => JSON.parse(line) as T)
}

export async function postNdjson<T>(path: string, data?: unknown): Promise<T[]> {
  const response = await api.post(path, { json: data })
  const text = await response.text()
  if (!text.trim()) return []
  return text.trim().split('\n').map((line) => JSON.parse(line) as T)
}

export { api }
