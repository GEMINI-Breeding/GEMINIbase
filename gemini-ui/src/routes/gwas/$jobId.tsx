import { useMemo } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Download, XCircle } from 'lucide-react'

import { jobsApi } from '@/api/endpoints/jobs'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { JobOutput, JSONB } from '@/api/types'

function statusVariant(status: string) {
  switch (status.toLowerCase()) {
    case 'completed': return 'default' as const
    case 'failed': return 'destructive' as const
    case 'running': return 'secondary' as const
    default: return 'outline' as const
  }
}

/**
 * Convert "s3://gemini/gwas/<id>/manhattan.png" → "/api/files/download/gemini/gwas/<id>/manhattan.png".
 * The files controller splits the path on '/' and takes [1] as bucket, so we preserve the
 * leading slash by matching the existing pattern used elsewhere in the UI.
 */
function s3UrlToDownload(s3: unknown): string | null {
  if (typeof s3 !== 'string') return null
  const m = s3.match(/^s3:\/\/([^/]+)\/(.+)$/)
  if (!m) return null
  const [, bucket, key] = m
  return `/api/files/download/${bucket}/${key}`
}

interface GwasArtifacts {
  manhattan?: string
  qq?: string
  assoc?: string
  kinship?: string
  qc_log?: string
  pca_eigenvec?: string
  covar?: string
  result_json?: string
  qc_bed?: string
  qc_bim?: string
  qc_fam?: string
  [k: string]: string | undefined
}

interface GwasResult {
  artifacts?: GwasArtifacts
  study_name?: string
  trait_ids?: string[]
  model?: string
  lmm_test?: string
  n_pcs_used?: number
  n_variants_input?: number
  n_variants_passed_qc?: number
  n_samples_input?: number
  n_samples_passed_qc?: number
  n_samples_with_phenotype?: number
  genomic_inflation_lambda?: number
  n_genome_wide_sig?: number
  n_suggestive?: number
  n_bonferroni_sig?: number
  bonferroni_threshold?: number
  p_column?: string
  top_hits?: Array<{
    rs: string
    chr?: number | null
    pos?: number | null
    p: number
    beta?: number
    se?: number
    af?: number
  }>
}

function GwasJobDetail() {
  const { jobId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: job, isLoading } = useQuery<JobOutput>({
    queryKey: ['jobs', jobId],
    queryFn: () => jobsApi.getById(jobId),
    refetchInterval: (query) => {
      const status = String(query.state.data?.status ?? '').toLowerCase()
      return status === 'running' || status === 'pending' ? 3000 : false
    },
  })

  const cancelMutation = useMutation({
    mutationFn: () => jobsApi.cancel(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs', jobId] }),
  })

  const result = useMemo<GwasResult | null>(() => {
    if (!job?.result) return null
    // result is JSONB (Record<string, unknown>); narrow to our shape.
    return job.result as unknown as GwasResult
  }, [job])

  const progressDetail = useMemo<Record<string, unknown> | null>(() => {
    if (!job?.progress_detail || typeof job.progress_detail !== 'object') return null
    return job.progress_detail as Record<string, unknown>
  }, [job])

  if (isLoading) return <div className="animate-pulse p-8">Loading…</div>
  if (!job) return <div className="p-8">Job not found</div>

  // Backend stores job.status as uppercase (PENDING / RUNNING / COMPLETED /
  // FAILED / CANCELLED). Normalise once here so every comparison below —
  // and the refetchInterval above — can use a single casing.
  const statusLower = String(job.status ?? '').toLowerCase()
  const canCancel = statusLower === 'pending' || statusLower === 'running'
  const progressPct = Math.round((job.progress ?? 0) * 100)
  const stage = progressDetail?.stage as string | undefined

  const manhattanSrc = s3UrlToDownload(result?.artifacts?.manhattan)
  const qqSrc = s3UrlToDownload(result?.artifacts?.qq)

  return (
    <div>
      <PageHeader
        title={`GWAS — ${result?.study_name ?? job.job_type}`}
        description={`Job ${jobId}`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/gwas' })}>
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Button>
            {canCancel && (
              <Button
                variant="destructive"
                onClick={() => cancelMutation.mutate()}
                disabled={cancelMutation.isPending}
              >
                <XCircle className="mr-2 h-4 w-4" /> Cancel
              </Button>
            )}
          </div>
        }
      />

      {/* Status + progress */}
      <section data-testid="gwas-status-card" className="rounded-md border p-4 mb-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
            {stage && <span className="text-sm text-muted-foreground">· {stage}</span>}
          </div>
          <span className="text-sm text-muted-foreground">{progressPct}%</span>
        </div>
        <div className="w-full h-2 rounded bg-muted overflow-hidden">
          <div
            className="h-full bg-primary transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        {progressDetail && Object.keys(progressDetail).length > 1 && (
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            {Object.entries(progressDetail).map(([k, v]) => (
              k === 'stage' ? null : (
                <div key={k}>
                  <span className="text-muted-foreground">{k}:</span>{' '}
                  <span className="font-mono">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                </div>
              )
            ))}
          </div>
        )}
      </section>

      {/* Error */}
      {job.error_message && (
        <section className="rounded-md border border-destructive bg-destructive/10 p-4 mb-4">
          <h3 className="text-sm font-semibold text-destructive mb-1">Error</h3>
          <pre className="text-xs whitespace-pre-wrap">{job.error_message}</pre>
        </section>
      )}

      {/* Results (only shown when COMPLETED) */}
      {statusLower === 'completed' && result && (
        <>
          <section data-testid="gwas-result-summary" className="rounded-md border p-4 mb-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Summary
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <Stat label="Model" value={result.model ?? '—'} />
              <Stat label="Test" value={result.lmm_test ?? '—'} />
              <Stat
                label="Variants (in → QC)"
                value={`${result.n_variants_input ?? '?'} → ${result.n_variants_passed_qc ?? '?'}`}
              />
              <Stat
                label="Samples (in → QC)"
                value={`${result.n_samples_input ?? '?'} → ${result.n_samples_passed_qc ?? '?'}`}
              />
              <Stat label="PCs used" value={String(result.n_pcs_used ?? 0)} />
              <Stat
                label="Genomic inflation λ"
                value={result.genomic_inflation_lambda?.toFixed(3) ?? '—'}
              />
              <Stat
                label="Genome-wide hits (p<5e-8)"
                value={String(result.n_genome_wide_sig ?? 0)}
              />
              <Stat
                label="Suggestive (p<1e-5)"
                value={String(result.n_suggestive ?? 0)}
              />
            </div>
          </section>

          {(manhattanSrc || qqSrc) && (
            <section className="rounded-md border p-4 mb-4">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Plots
              </h3>
              <div className="grid gap-4 md:grid-cols-[2fr_1fr]">
                {manhattanSrc && (
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Manhattan</p>
                    <img
                      data-testid="gwas-manhattan-img"
                      src={manhattanSrc}
                      alt="Manhattan plot"
                      className="w-full border rounded"
                    />
                  </div>
                )}
                {qqSrc && (
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">QQ</p>
                    <img
                      data-testid="gwas-qq-img"
                      src={qqSrc}
                      alt="QQ plot"
                      className="w-full border rounded"
                    />
                  </div>
                )}
              </div>
            </section>
          )}

          {result.top_hits && result.top_hits.length > 0 && (
            <section className="rounded-md border p-4 mb-4">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Top hits
              </h3>
              <div className="overflow-x-auto">
                <table data-testid="gwas-top-hits-table" className="w-full text-sm">
                  <thead className="bg-muted/50 text-left">
                    <tr>
                      <th className="px-3 py-2 font-medium">Variant</th>
                      <th className="px-3 py-2 font-medium">Chr</th>
                      <th className="px-3 py-2 font-medium">Pos</th>
                      <th className="px-3 py-2 font-medium">p ({result.p_column ?? 'wald'})</th>
                      <th className="px-3 py-2 font-medium">β</th>
                      <th className="px-3 py-2 font-medium">SE</th>
                      <th className="px-3 py-2 font-medium">AF</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.top_hits.map((hit) => (
                      <tr key={hit.rs} className="border-t">
                        <td className="px-3 py-2 font-mono">{hit.rs}</td>
                        <td className="px-3 py-2">{hit.chr ?? '—'}</td>
                        <td className="px-3 py-2">{hit.pos ?? '—'}</td>
                        <td className="px-3 py-2 font-mono">{hit.p.toExponential(2)}</td>
                        <td className="px-3 py-2">{hit.beta?.toFixed(3) ?? '—'}</td>
                        <td className="px-3 py-2">{hit.se?.toFixed(3) ?? '—'}</td>
                        <td className="px-3 py-2">{hit.af?.toFixed(3) ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {result.artifacts && (
            <section className="rounded-md border p-4 mb-4">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Artifacts
              </h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(result.artifacts).map(([name, url]) => {
                  const href = s3UrlToDownload(url)
                  if (!href) return null
                  return (
                    <a
                      key={name}
                      href={href}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 rounded border px-2 py-1 text-xs hover:bg-muted"
                    >
                      <Download className="h-3 w-3" />
                      {name}
                    </a>
                  )
                })}
              </div>
            </section>
          )}
        </>
      )}

      {/* Raw parameters (always handy) */}
      {job.parameters && (
        <section className="rounded-md border p-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Parameters
          </h3>
          <pre className="text-xs font-mono whitespace-pre-wrap">
            {JSON.stringify(job.parameters as JSONB, null, 2)}
          </pre>
        </section>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  )
}

export const Route = createFileRoute('/gwas/$jobId')({ component: GwasJobDetail })
