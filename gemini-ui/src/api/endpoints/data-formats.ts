import { get, post, patch, del } from '@/api/client'
import type { DataFormatOutput, DataFormatInput, DataFormatUpdate } from '@/api/types'

export const dataFormatsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<DataFormatOutput[]>('api/data_formats/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<DataFormatOutput[]>('api/data_formats', params),

  getById: (id: string) =>
    get<DataFormatOutput>(`api/data_formats/id/${id}`),

  create: (data: DataFormatInput) =>
    post<DataFormatOutput>('api/data_formats', data),

  update: (id: string, data: DataFormatUpdate) =>
    patch<DataFormatOutput>(`api/data_formats/id/${id}`, data),

  remove: (id: string) =>
    del(`api/data_formats/id/${id}`),
}
