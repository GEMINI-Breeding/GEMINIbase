import { get, post, patch, del } from '@/api/client'
import type { SeasonOutput, SeasonInput, SeasonUpdate } from '@/api/types'

export const seasonsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<SeasonOutput[]>('api/seasons/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<SeasonOutput[]>('api/seasons', params),

  getById: (id: string) =>
    get<SeasonOutput>(`api/seasons/id/${id}`),

  create: (data: SeasonInput) =>
    post<SeasonOutput>('api/seasons', data),

  update: (id: string, data: SeasonUpdate) =>
    patch<SeasonOutput>(`api/seasons/id/${id}`, data),

  remove: (id: string) =>
    del(`api/seasons/id/${id}`),
}
