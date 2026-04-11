import { get, getOrEmpty, post, patch, del } from '@/api/client'
import type {
  ExperimentOutput,
  ExperimentInput,
  ExperimentUpdate,
  SeasonOutput,
  SiteOutput,
  PopulationOutput,
  SensorOutput,
  SensorPlatformOutput,
  TraitOutput,
  DatasetOutput,
  GenotypeOutput,
} from '@/api/types'

export const experimentsApi = {
  getAll: (limit = 100, offset = 0) =>
    get<ExperimentOutput[]>('api/experiments/all', { limit, offset }),

  search: (params: Record<string, unknown>) =>
    get<ExperimentOutput[]>('api/experiments', params),

  getById: (id: string) =>
    get<ExperimentOutput>(`api/experiments/id/${id}`),

  create: (data: ExperimentInput) =>
    post<ExperimentOutput>('api/experiments', data),

  update: (id: string, data: ExperimentUpdate) =>
    patch<ExperimentOutput>(`api/experiments/id/${id}`, data),

  remove: (id: string) =>
    del(`api/experiments/id/${id}`),

  getHierarchy: (id: string) =>
    get<unknown>(`api/experiments/id/${id}/hierarchy`),

  // Association queries use getOrEmpty to handle 404 (no results) as empty arrays
  getSeasons: (id: string) =>
    getOrEmpty<SeasonOutput>(`api/experiments/id/${id}/seasons`),

  getSites: (id: string) =>
    getOrEmpty<SiteOutput>(`api/experiments/id/${id}/sites`),

  getPopulations: (id: string) =>
    getOrEmpty<PopulationOutput>(`api/experiments/id/${id}/populations`),

  getSensors: (id: string) =>
    getOrEmpty<SensorOutput>(`api/experiments/id/${id}/sensors`),

  getSensorPlatforms: (id: string) =>
    getOrEmpty<SensorPlatformOutput>(`api/experiments/id/${id}/sensor_platforms`),

  getTraits: (id: string) =>
    getOrEmpty<TraitOutput>(`api/experiments/id/${id}/traits`),

  getDatasets: (id: string) =>
    getOrEmpty<DatasetOutput>(`api/experiments/id/${id}/datasets`),

  getGenotypes: (id: string) =>
    getOrEmpty<GenotypeOutput>(`api/experiments/id/${id}/genotypes`),
}
