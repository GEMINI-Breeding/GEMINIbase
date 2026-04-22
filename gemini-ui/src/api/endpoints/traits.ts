import { get, getOrEmpty, getNdjson, post, postNdjson, patch, del } from '@/api/client'
import type {
  TraitOutput,
  TraitInput,
  TraitUpdate,
  TraitRecordOutput,
  TraitRecordFilter,
} from '@/api/types'

export const traitsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<TraitOutput[]>('api/traits/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<TraitOutput[]>('api/traits', params),

  getById: (id: string) =>
    get<TraitOutput>(`api/traits/id/${id}`),

  create: (data: TraitInput) =>
    post<TraitOutput>('api/traits', data),

  update: (id: string, data: TraitUpdate) =>
    patch<TraitOutput>(`api/traits/id/${id}`, data),

  remove: (id: string) =>
    del(`api/traits/id/${id}`),

  getRecords: (traitId: string, params?: Record<string, unknown>) =>
    getNdjson<TraitRecordOutput>(`api/traits/id/${traitId}/records`, params),

  filterRecords: (traitId: string, filter: TraitRecordFilter) =>
    postNdjson<TraitRecordOutput>(`api/traits/id/${traitId}/records/filter`, filter),

  getExperiments: (traitId: string) =>
    getOrEmpty<string>(`api/traits/id/${traitId}/experiments`),

  getDatasets: (traitId: string) =>
    getOrEmpty<{ id: string; dataset_name: string }>(`api/traits/id/${traitId}/datasets`),

  bulkCreateRecords: (traitId: string, data: {
    records: Record<string, unknown>[]
    experiment_name?: string
    season_name?: string
    site_name?: string
    dataset_name?: string
    collection_date?: string
  }) =>
    post<{ inserted_count: number; record_ids: string[] }>(`api/traits/id/${traitId}/records/bulk`, data),
}
