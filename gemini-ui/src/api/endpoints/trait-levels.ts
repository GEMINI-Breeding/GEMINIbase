import { get, post, patch, del } from '@/api/client'
import type { TraitLevelOutput, TraitLevelInput, TraitLevelUpdate } from '@/api/types'

export const traitLevelsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<TraitLevelOutput[]>('api/trait_levels/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<TraitLevelOutput[]>('api/trait_levels', params),

  getById: (id: string) =>
    get<TraitLevelOutput>(`api/trait_levels/id/${id}`),

  create: (data: TraitLevelInput) =>
    post<TraitLevelOutput>('api/trait_levels', data),

  update: (id: string, data: TraitLevelUpdate) =>
    patch<TraitLevelOutput>(`api/trait_levels/id/${id}`, data),

  remove: (id: string) =>
    del(`api/trait_levels/id/${id}`),
}
