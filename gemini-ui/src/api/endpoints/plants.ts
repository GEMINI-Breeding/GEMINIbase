import { get, post, patch, del } from '@/api/client'
import type { PlantOutput, PlantInput, PlantUpdate } from '@/api/types'

export const plantsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<PlantOutput[]>('api/plants/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<PlantOutput[]>('api/plants', params),

  getById: (id: string) =>
    get<PlantOutput>(`api/plants/id/${id}`),

  create: (data: PlantInput) =>
    post<PlantOutput>('api/plants', data),

  update: (id: string, data: PlantUpdate) =>
    patch<PlantOutput>(`api/plants/id/${id}`, data),

  remove: (id: string) =>
    del(`api/plants/id/${id}`),
}
