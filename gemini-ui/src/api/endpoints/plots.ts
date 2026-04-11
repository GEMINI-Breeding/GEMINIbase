import { get, post, patch, del } from '@/api/client'
import type { PlotOutput, PlotInput, PlotUpdate } from '@/api/types'

export const plotsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<PlotOutput[]>('api/plots/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<PlotOutput[]>('api/plots', params),

  getById: (id: string) =>
    get<PlotOutput>(`api/plots/id/${id}`),

  create: (data: PlotInput) =>
    post<PlotOutput>('api/plots', data),

  update: (id: string, data: PlotUpdate) =>
    patch<PlotOutput>(`api/plots/id/${id}`, data),

  remove: (id: string) =>
    del(`api/plots/id/${id}`),
}
