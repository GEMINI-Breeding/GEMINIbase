import { get, post, patch, del } from '@/api/client'
import type {
  ScriptOutput,
  ScriptInput,
  ScriptUpdate,
  ScriptRunOutput,
  ScriptRecordOutput,
  ScriptRecordFilter,
} from '@/api/types'

export const scriptsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<ScriptOutput[]>('api/scripts/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<ScriptOutput[]>('api/scripts', params),

  getById: (id: string) =>
    get<ScriptOutput>(`api/scripts/id/${id}`),

  create: (data: ScriptInput) =>
    post<ScriptOutput>('api/scripts', data),

  update: (id: string, data: ScriptUpdate) =>
    patch<ScriptOutput>(`api/scripts/id/${id}`, data),

  remove: (id: string) =>
    del(`api/scripts/id/${id}`),

  getRuns: (id: string, limit = 100, offset = 0) =>
    get<ScriptRunOutput[]>(`api/scripts/id/${id}/runs`, { limit, offset }),

  getRecords: (id: string, limit = 100, offset = 0) =>
    get<ScriptRecordOutput[]>(`api/scripts/id/${id}/records`, { limit, offset }),

  filterRecords: (id: string, filter: ScriptRecordFilter) =>
    get<ScriptRecordOutput[]>(`api/scripts/id/${id}/records/filter`, filter as unknown as Record<string, unknown>),
}
