import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query'

interface CrudApi<TOutput, TInput, TUpdate> {
  getAll: (limit?: number, offset?: number) => Promise<TOutput[]>
  search: (params: Record<string, unknown>) => Promise<TOutput[]>
  getById: (id: string) => Promise<TOutput>
  create: (data: TInput) => Promise<TOutput>
  update: (id: string, data: TUpdate) => Promise<TOutput>
  remove: (id: string) => Promise<void>
}

// Wraps a list-returning API call to return [] on 404 (backend returns 404 for empty results)
async function safeList<T>(fn: () => Promise<T[]>): Promise<T[]> {
  try {
    const result = await fn()
    return Array.isArray(result) ? result : []
  } catch (err) {
    if (err instanceof Error && 'response' in err) {
      const response = (err as { response: Response }).response
      if (response.status === 404) return []
    }
    throw err
  }
}

export function createCrudHooks<TOutput, TInput, TUpdate>(
  entityKey: string,
  api: CrudApi<TOutput, TInput, TUpdate>,
) {
  function useGetAll(limit = 100, offset = 0, options?: Partial<UseQueryOptions<TOutput[]>>) {
    return useQuery({
      queryKey: [entityKey, 'list', limit, offset],
      queryFn: () => safeList(() => api.getAll(limit, offset)),
      ...options,
    })
  }

  function useSearch(params: Record<string, unknown>, options?: Partial<UseQueryOptions<TOutput[]>>) {
    return useQuery({
      queryKey: [entityKey, 'search', params],
      queryFn: () => safeList(() => api.search(params)),
      enabled: Object.values(params).some((v) => v != null && v !== ''),
      ...options,
    })
  }

  function useGetById(id: string | undefined, options?: Partial<UseQueryOptions<TOutput>>) {
    return useQuery({
      queryKey: [entityKey, id],
      queryFn: () => api.getById(id!),
      enabled: !!id,
      ...options,
    })
  }

  function useCreate() {
    const queryClient = useQueryClient()
    return useMutation({
      mutationFn: (data: TInput) => api.create(data),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: [entityKey] })
      },
    })
  }

  function useUpdate() {
    const queryClient = useQueryClient()
    return useMutation({
      mutationFn: ({ id, data }: { id: string; data: TUpdate }) => api.update(id, data),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: [entityKey] })
      },
    })
  }

  function useRemove() {
    const queryClient = useQueryClient()
    return useMutation({
      mutationFn: (id: string) => api.remove(id),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: [entityKey] })
      },
    })
  }

  return { useGetAll, useSearch, useGetById, useCreate, useUpdate, useRemove }
}
