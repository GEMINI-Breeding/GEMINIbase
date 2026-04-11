import { get, post, patch, del } from '@/api/client'
import type { SensorTypeOutput, SensorTypeInput, SensorTypeUpdate } from '@/api/types'

export const sensorTypesApi = {
  getAll: (limit = 100, offset = 0) =>
    get<SensorTypeOutput[]>('api/sensor_types/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<SensorTypeOutput[]>('api/sensor_types', params),

  getById: (id: string) =>
    get<SensorTypeOutput>(`api/sensor_types/id/${id}`),

  create: (data: SensorTypeInput) =>
    post<SensorTypeOutput>('api/sensor_types', data),

  update: (id: string, data: SensorTypeUpdate) =>
    patch<SensorTypeOutput>(`api/sensor_types/id/${id}`, data),

  remove: (id: string) =>
    del(`api/sensor_types/id/${id}`),
}
