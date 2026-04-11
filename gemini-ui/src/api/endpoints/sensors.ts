import { get, post, patch, del } from '@/api/client'
import type {
  SensorOutput,
  SensorInput,
  SensorUpdate,
  SensorRecordOutput,
  SensorRecordFilter,
} from '@/api/types'

export const sensorsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<SensorOutput[]>('api/sensors/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<SensorOutput[]>('api/sensors', params),

  getById: (id: string) =>
    get<SensorOutput>(`api/sensors/id/${id}`),

  create: (data: SensorInput) =>
    post<SensorOutput>('api/sensors', data),

  update: (id: string, data: SensorUpdate) =>
    patch<SensorOutput>(`api/sensors/id/${id}`, data),

  remove: (id: string) =>
    del(`api/sensors/id/${id}`),

  getRecords: (sensorId: string, limit = 100, offset = 0) =>
    get<SensorRecordOutput[]>(`api/sensors/id/${sensorId}/records`, { limit, offset }),

  filterRecords: (sensorId: string, filter: SensorRecordFilter) =>
    post<SensorRecordOutput[]>(`api/sensors/id/${sensorId}/records/filter`, filter),
}
