import { get, post, patch, del } from '@/api/client'
import type { JobOutput, JobSubmitInput, JobStatusUpdate } from '@/api/types'

export const jobsApi = {
  submit: (data: JobSubmitInput) =>
    post<JobOutput>('api/jobs/submit', data),

  getById: (id: string) =>
    get<JobOutput>(`api/jobs/${id}`),

  getAll: (params?: Record<string, unknown>) =>
    get<JobOutput[]>('api/jobs/all', params),

  cancel: (id: string) =>
    post<JobOutput>(`api/jobs/${id}/cancel`),

  remove: (id: string) =>
    del(`api/jobs/${id}`),

  updateStatus: (id: string, data: JobStatusUpdate) =>
    patch<JobOutput>(`api/jobs/${id}/status`, data),
}
