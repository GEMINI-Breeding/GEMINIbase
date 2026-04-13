import { get, post, patch, del } from '@/api/client'
import type { LineOutput, LineInput, LineUpdate } from '@/api/types'

export const linesApi = {
  getAll: (limit = 100, offset = 0) => get<LineOutput[]>('api/lines/all', { limit, offset }),
  search: (params: Record<string, unknown>) => get<LineOutput[]>('api/lines', params),
  getById: (id: string) => get<LineOutput>(`api/lines/id/${id}`),
  create: (data: LineInput) => post<LineOutput>('api/lines', data),
  update: (id: string, data: LineUpdate) => patch<LineOutput>(`api/lines/id/${id}`, data),
  remove: (id: string) => del(`api/lines/id/${id}`),
}
