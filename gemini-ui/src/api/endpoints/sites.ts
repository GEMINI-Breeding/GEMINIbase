import { get, post, patch, del } from '@/api/client'
import type { SiteOutput, SiteInput, SiteUpdate } from '@/api/types'

export const sitesApi = {
  getAll: (limit = 100, offset = 0) =>
    get<SiteOutput[]>('api/sites/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<SiteOutput[]>('api/sites', params),

  getById: (id: string) =>
    get<SiteOutput>(`api/sites/id/${id}`),

  create: (data: SiteInput) =>
    post<SiteOutput>('api/sites', data),

  update: (id: string, data: SiteUpdate) =>
    patch<SiteOutput>(`api/sites/id/${id}`, data),

  remove: (id: string) =>
    del(`api/sites/id/${id}`),
}
