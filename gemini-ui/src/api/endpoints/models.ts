import { get, post, patch, del } from '@/api/client'
import type {
  ModelOutput,
  ModelInput,
  ModelUpdate,
  ModelRunOutput,
  ModelRecordOutput,
  ModelRecordFilter,
} from '@/api/types'

export const modelsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<ModelOutput[]>('api/models/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<ModelOutput[]>('api/models', params),

  getById: (id: string) =>
    get<ModelOutput>(`api/models/id/${id}`),

  create: (data: ModelInput) =>
    post<ModelOutput>('api/models', data),

  update: (id: string, data: ModelUpdate) =>
    patch<ModelOutput>(`api/models/id/${id}`, data),

  remove: (id: string) =>
    del(`api/models/id/${id}`),

  getRuns: (id: string, limit = 100, offset = 0) =>
    get<ModelRunOutput[]>(`api/models/id/${id}/runs`, { limit, offset }),

  getRecords: (id: string, limit = 100, offset = 0) =>
    get<ModelRecordOutput[]>(`api/models/id/${id}/records`, { limit, offset }),

  filterRecords: (id: string, filter: ModelRecordFilter) =>
    get<ModelRecordOutput[]>(`api/models/id/${id}/records/filter`, filter as unknown as Record<string, unknown>),
}
