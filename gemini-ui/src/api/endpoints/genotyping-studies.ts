import { get, post, patch, del, getBlob } from '@/api/client'
import type {
  GenotypingStudyOutput,
  GenotypingStudyInput,
  GenotypingStudyUpdate,
  GenotypeRecordOutput,
  GenotypeMatrixBatchInput,
  GenotypeMatrixBatchResult,
} from '@/api/types'

export const genotypingStudiesApi = {
  getAll: (limit = 100, offset = 0) => get<GenotypingStudyOutput[]>('api/genotyping_studies/all', { limit, offset }),
  search: (params: Record<string, unknown>) => get<GenotypingStudyOutput[]>('api/genotyping_studies', params),
  getById: (id: string) => get<GenotypingStudyOutput>(`api/genotyping_studies/id/${id}`),
  create: (data: GenotypingStudyInput) => post<GenotypingStudyOutput>('api/genotyping_studies', data),
  update: (id: string, data: GenotypingStudyUpdate) => patch<GenotypingStudyOutput>(`api/genotyping_studies/id/${id}`, data),
  remove: (id: string) => del(`api/genotyping_studies/id/${id}`),
  getRecords: (id: string, limit = 100, offset = 0) => get<GenotypeRecordOutput[]>(`api/genotyping_studies/id/${id}/records`, { limit, offset }),
  exportData: (id: string, format = 'hapmap', coding = 'numerical') => get<string>(`api/genotyping_studies/id/${id}/export`, { format, coding }),
  /** Binary download variant — triggers the browser to save the file. */
  exportBlob: (id: string, format = 'hapmap', coding = 'numerical') =>
    getBlob(
      `api/genotyping_studies/id/${id}/export?format=${encodeURIComponent(format)}&coding=${encodeURIComponent(coding)}`,
    ),
  ingestMatrix: (id: string, batch: GenotypeMatrixBatchInput) =>
    post<GenotypeMatrixBatchResult>(`api/genotyping_studies/id/${id}/ingest-matrix`, batch),
}
