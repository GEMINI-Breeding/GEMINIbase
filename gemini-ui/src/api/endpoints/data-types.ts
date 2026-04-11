import { get, post, patch, del } from '@/api/client'
import type { DataTypeOutput, DataTypeInput, DataTypeUpdate } from '@/api/types'

export const dataTypesApi = {
  getAll: (limit = 100, offset = 0) =>
    get<DataTypeOutput[]>('api/data_types/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<DataTypeOutput[]>('api/data_types', params),

  getById: (id: string) =>
    get<DataTypeOutput>(`api/data_types/id/${id}`),

  create: (data: DataTypeInput) =>
    post<DataTypeOutput>('api/data_types', data),

  update: (id: string, data: DataTypeUpdate) =>
    patch<DataTypeOutput>(`api/data_types/id/${id}`, data),

  remove: (id: string) =>
    del(`api/data_types/id/${id}`),
}
