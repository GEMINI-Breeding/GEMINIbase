import { get, post, patch, del } from '@/api/client'
import type {
  ProcedureOutput,
  ProcedureInput,
  ProcedureUpdate,
  ProcedureRunOutput,
  ProcedureRecordOutput,
  ProcedureRecordFilter,
} from '@/api/types'

export const proceduresApi = {
  getAll: (limit = 100, offset = 0) =>
    get<ProcedureOutput[]>('api/procedures/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<ProcedureOutput[]>('api/procedures', params),

  getById: (id: string) =>
    get<ProcedureOutput>(`api/procedures/id/${id}`),

  create: (data: ProcedureInput) =>
    post<ProcedureOutput>('api/procedures', data),

  update: (id: string, data: ProcedureUpdate) =>
    patch<ProcedureOutput>(`api/procedures/id/${id}`, data),

  remove: (id: string) =>
    del(`api/procedures/id/${id}`),

  getRuns: (id: string, limit = 100, offset = 0) =>
    get<ProcedureRunOutput[]>(`api/procedures/id/${id}/runs`, { limit, offset }),

  getRecords: (id: string, limit = 100, offset = 0) =>
    get<ProcedureRecordOutput[]>(`api/procedures/id/${id}/records`, { limit, offset }),

  filterRecords: (id: string, filter: ProcedureRecordFilter) =>
    get<ProcedureRecordOutput[]>(`api/procedures/id/${id}/records/filter`, filter as unknown as Record<string, unknown>),
}
