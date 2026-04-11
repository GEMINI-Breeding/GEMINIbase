import { get, post, patch, del } from '@/api/client'
import type {
  GenotypeOutput,
  GenotypeInput,
  GenotypeUpdate,
  GenotypeRecordOutput,
} from '@/api/types'

export const genotypesApi = {
  getAll: (limit = 100, offset = 0) =>
    get<GenotypeOutput[]>('api/genotypes/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<GenotypeOutput[]>('api/genotypes', params),

  getById: (id: string) =>
    get<GenotypeOutput>(`api/genotypes/id/${id}`),

  create: (data: GenotypeInput) =>
    post<GenotypeOutput>('api/genotypes', data),

  update: (id: string, data: GenotypeUpdate) =>
    patch<GenotypeOutput>(`api/genotypes/id/${id}`, data),

  remove: (id: string) =>
    del(`api/genotypes/id/${id}`),

  getRecords: (id: string, limit = 100, offset = 0) =>
    get<GenotypeRecordOutput[]>(`api/genotypes/id/${id}/records`, { limit, offset }),

  exportData: (id: string, format = 'hapmap', coding = 'numerical') =>
    get<string>(`api/genotypes/id/${id}/export`, { format, coding }),
}
