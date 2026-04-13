import { get, post, patch, del } from '@/api/client'
import type { AccessionOutput, AccessionInput, AccessionUpdate } from '@/api/types'

export const accessionsApi = {
  getAll: (limit = 100, offset = 0) => get<AccessionOutput[]>('api/accessions/all', { limit, offset }),
  search: (params: Record<string, unknown>) => get<AccessionOutput[]>('api/accessions', params),
  getById: (id: string) => get<AccessionOutput>(`api/accessions/id/${id}`),
  create: (data: AccessionInput) => post<AccessionOutput>('api/accessions', data),
  update: (id: string, data: AccessionUpdate) => patch<AccessionOutput>(`api/accessions/id/${id}`, data),
  remove: (id: string) => del(`api/accessions/id/${id}`),
}
