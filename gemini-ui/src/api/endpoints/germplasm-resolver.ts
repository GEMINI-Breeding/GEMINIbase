import { post } from '@/api/client'

export type ResolveMatchKind =
  | 'accession_exact'
  | 'line_exact'
  | 'alias_experiment'
  | 'alias_global'
  | 'fuzzy_accession'
  | 'fuzzy_line'
  | 'unresolved'

export interface ResolveCandidate {
  id: string
  kind: 'accession' | 'line'
  name: string
  score: number
}

export interface ResolveResult {
  input_name: string
  match_kind: ResolveMatchKind
  accession_id?: string | null
  line_id?: string | null
  canonical_name?: string | null
  candidates: ResolveCandidate[]
}

export interface ResolveRequest {
  names: string[]
  experiment_id?: string | null
}

export interface ResolveResponse {
  results: ResolveResult[]
}

export interface AliasBulkEntry {
  alias: string
  accession_name?: string | null
  line_name?: string | null
  source?: string | null
}

export interface AliasBulkRequest {
  scope: 'global' | 'experiment'
  experiment_id?: string | null
  entries: AliasBulkEntry[]
}

export interface AliasBulkError {
  index: number
  alias: string
  reason: string
}

export interface AliasBulkResponse {
  created: number
  updated: number
  errors: AliasBulkError[]
}

// Normalize alias / name cells before sending to the resolver. The backend
// treats inputs as already-canonical whitespace.
export const normalizeGermplasmName = (raw: string | null | undefined): string =>
  (raw ?? '').toString().trim()

export const germplasmResolverApi = {
  resolve: (data: ResolveRequest) =>
    post<ResolveResponse>('api/germplasm/resolve', {
      ...data,
      names: data.names.map(normalizeGermplasmName),
    }),
  bulkAliases: (data: AliasBulkRequest) =>
    post<AliasBulkResponse>('api/germplasm/aliases/bulk', {
      ...data,
      entries: data.entries.map((e) => ({
        ...e,
        alias: normalizeGermplasmName(e.alias),
        accession_name: e.accession_name ? normalizeGermplasmName(e.accession_name) : null,
        line_name: e.line_name ? normalizeGermplasmName(e.line_name) : null,
      })),
    }),
}
