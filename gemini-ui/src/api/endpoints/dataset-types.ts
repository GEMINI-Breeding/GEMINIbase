import { get, post, patch, del } from '@/api/client'
import type { DatasetTypeOutput, DatasetTypeInput, DatasetTypeUpdate } from '@/api/types'

export const datasetTypesApi = {
  getAll: (limit = 100, offset = 0) =>
    get<DatasetTypeOutput[]>('api/dataset_types/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<DatasetTypeOutput[]>('api/dataset_types', params),

  getById: (id: string) =>
    get<DatasetTypeOutput>(`api/dataset_types/id/${id}`),

  create: (data: DatasetTypeInput) =>
    post<DatasetTypeOutput>('api/dataset_types', data),

  update: (id: string, data: DatasetTypeUpdate) =>
    patch<DatasetTypeOutput>(`api/dataset_types/id/${id}`, data),

  remove: (id: string) =>
    del(`api/dataset_types/id/${id}`),
}
