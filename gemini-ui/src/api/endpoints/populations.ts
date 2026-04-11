import { get, post, patch, del } from '@/api/client'
import type { PopulationOutput, PopulationInput, PopulationUpdate } from '@/api/types'

export const populationsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<PopulationOutput[]>('api/populations/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<PopulationOutput[]>('api/populations', params),

  getById: (id: string) =>
    get<PopulationOutput>(`api/populations/id/${id}`),

  create: (data: PopulationInput) =>
    post<PopulationOutput>('api/populations', data),

  update: (id: string, data: PopulationUpdate) =>
    patch<PopulationOutput>(`api/populations/id/${id}`, data),

  remove: (id: string) =>
    del(`api/populations/id/${id}`),
}
