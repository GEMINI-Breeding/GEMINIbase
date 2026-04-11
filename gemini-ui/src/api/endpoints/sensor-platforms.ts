import { get, post, patch, del } from '@/api/client'
import type {
  SensorPlatformOutput,
  SensorPlatformInput,
  SensorPlatformUpdate,
} from '@/api/types'

export const sensorPlatformsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<SensorPlatformOutput[]>('api/sensor_platforms/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<SensorPlatformOutput[]>('api/sensor_platforms', params),

  getById: (id: string) =>
    get<SensorPlatformOutput>(`api/sensor_platforms/id/${id}`),

  create: (data: SensorPlatformInput) =>
    post<SensorPlatformOutput>('api/sensor_platforms', data),

  update: (id: string, data: SensorPlatformUpdate) =>
    patch<SensorPlatformOutput>(`api/sensor_platforms/id/${id}`, data),

  remove: (id: string) =>
    del(`api/sensor_platforms/id/${id}`),
}
