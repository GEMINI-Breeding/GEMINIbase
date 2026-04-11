import { get, post, patch, del } from '@/api/client'
import type {
  VariantOutput,
  VariantInput,
  VariantUpdate,
  VariantBulkInput,
} from '@/api/types'

export const variantsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<VariantOutput[]>('api/variants/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<VariantOutput[]>('api/variants', params),

  getById: (id: string) =>
    get<VariantOutput>(`api/variants/id/${id}`),

  create: (data: VariantInput) =>
    post<VariantOutput>('api/variants', data),

  update: (id: string, data: VariantUpdate) =>
    patch<VariantOutput>(`api/variants/id/${id}`, data),

  remove: (id: string) =>
    del(`api/variants/id/${id}`),

  bulkCreate: (data: VariantBulkInput) =>
    post<{ inserted_count: number; ids: string[] }>('api/variants/bulk', data),
}
