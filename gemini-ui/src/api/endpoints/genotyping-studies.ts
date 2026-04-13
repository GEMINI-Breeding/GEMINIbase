import { get, post, patch, del } from '@/api/client'
import type { GenotypingStudyOutput, GenotypingStudyInput, GenotypingStudyUpdate, GenotypeRecordOutput } from '@/api/types'

export const genotypingStudiesApi = {
  getAll: (limit = 100, offset = 0) => get<GenotypingStudyOutput[]>('api/genotyping_studies/all', { limit, offset }),
  search: (params: Record<string, unknown>) => get<GenotypingStudyOutput[]>('api/genotyping_studies', params),
  getById: (id: string) => get<GenotypingStudyOutput>(`api/genotyping_studies/id/${id}`),
  create: (data: GenotypingStudyInput) => post<GenotypingStudyOutput>('api/genotyping_studies', data),
  update: (id: string, data: GenotypingStudyUpdate) => patch<GenotypingStudyOutput>(`api/genotyping_studies/id/${id}`, data),
  remove: (id: string) => del(`api/genotyping_studies/id/${id}`),
  getRecords: (id: string, limit = 100, offset = 0) => get<GenotypeRecordOutput[]>(`api/genotyping_studies/id/${id}/records`, { limit, offset }),
  exportData: (id: string, format = 'hapmap', coding = 'numerical') => get<string>(`api/genotyping_studies/id/${id}/export`, { format, coding }),
}
