import { get, getOrEmpty, post, patch, del } from '@/api/client'
import type {
  DatasetOutput,
  DatasetInput,
  DatasetUpdate,
  DatasetRecordOutput,
  DatasetRecordFilter,
  ExperimentOutput,
} from '@/api/types'

export const datasetsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<DatasetOutput[]>('api/datasets/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<DatasetOutput[]>('api/datasets', params),

  getById: (id: string) =>
    get<DatasetOutput>(`api/datasets/id/${id}`),

  create: (data: DatasetInput) =>
    post<DatasetOutput>('api/datasets', data),

  update: (id: string, data: DatasetUpdate) =>
    patch<DatasetOutput>(`api/datasets/id/${id}`, data),

  remove: (id: string) =>
    del(`api/datasets/id/${id}`),

  getRecords: (id: string, limit = 100, offset = 0) =>
    get<DatasetRecordOutput[]>(`api/datasets/id/${id}/records`, { limit, offset }),

  filterRecords: (id: string, filter: DatasetRecordFilter) =>
    post<DatasetRecordOutput[]>(`api/datasets/id/${id}/records/filter`, filter),

  getExperiments: (id: string) =>
    getOrEmpty<ExperimentOutput>(`api/datasets/id/${id}/experiments`),
}
