import ky from 'ky'

const api = ky.create({
  prefix: import.meta.env.VITE_API_BASE_URL || '/',
  timeout: 30000,
  hooks: {
    beforeRequest: [
      ({ request }) => {
        const apiKey = import.meta.env.VITE_API_KEY
        if (apiKey) {
          request.headers.set('X-API-Key', apiKey)
        }
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

export async function del(path: string): Promise<void> {
  await api.delete(path)
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

export { api }
