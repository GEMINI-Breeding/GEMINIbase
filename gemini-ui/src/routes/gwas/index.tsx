import { useMemo, useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Play, ChevronDown, ChevronRight } from 'lucide-react'

import { gwasApi } from '@/api/endpoints/gwas'
import { jobsApi } from '@/api/endpoints/jobs'
import { datasetsApi } from '@/api/endpoints/datasets'
import {
  useExperiments,
  useDatasets,
  useGenotypingStudies,
} from '@/hooks/use-entity-hooks'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import type {
  GwasSubmitInput,
  JobOutput,
  ID,
} from '@/api/types'

type Model = 'lmm' | 'mvlmm' | 'bslmm'
type LmmTest = 'wald' | 'lrt' | 'score' | 'all'
type Agg = 'mean' | 'median' | 'first'

function statusVariant(status: string) {
  switch (status.toLowerCase()) {
    case 'completed': return 'default' as const
    case 'failed': return 'destructive' as const
    case 'running': return 'secondary' as const
    default: return 'outline' as const
  }
}

function GwasLanding() {
  const navigate = useNavigate()

  const [experimentId, setExperimentId] = useState<string>('')
  const [datasetId, setDatasetId] = useState<string>('')
  const [selectedTraits, setSelectedTraits] = useState<Set<string>>(new Set())
  const [studyId, setStudyId] = useState<string>('')

  const [model, setModel] = useState<Model>('lmm')
  const [lmmTest, setLmmTest] = useState<LmmTest>('wald')
  const [nPcs, setNPcs] = useState<number>(3)
  const [phenotypeAgg, setPhenotypeAgg] = useState<Agg>('mean')
  const [maf, setMaf] = useState<number>(0.05)
  const [geno, setGeno] = useState<number>(0.1)
  const [mind, setMind] = useState<number>(0.1)
  const [hwe, setHwe] = useState<number>(1e-6)

  const [showAdvanced, setShowAdvanced] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // --- Data sources ---
  const { data: experiments } = useExperiments.useGetAll(500)
  const { data: studies } = useGenotypingStudies.useGetAll(500)

  const experimentName = useMemo(
    () => experiments?.find((e) => e.id === experimentId)?.experiment_name,
    [experiments, experimentId],
  )
  const { data: datasets } = useDatasets.useSearch(
    experimentName ? { experiment_name: experimentName } : {},
  )
  // Traits filtered by the selected dataset via the dedicated dataset→traits
  // endpoint. The generic /api/traits search doesn't accept dataset_name and
  // silently defaults experiment_name to "Experiment A", returning empty.
  const { data: traits } = useQuery({
    queryKey: ['datasets', datasetId, 'traits'],
    queryFn: () => datasetsApi.getTraits(datasetId),
    enabled: !!datasetId,
  })

  // --- Recent GWAS jobs (polled) ---
  const { data: recentJobs } = useQuery<JobOutput[]>({
    queryKey: ['jobs', 'gwas-recent'],
    queryFn: () => jobsApi.getAll({ job_type: 'RUN_GWAS', limit: 20 }),
    refetchInterval: 5000,
  })

  // --- Submit mutation ---
  const submitMutation = useMutation({
    mutationFn: (data: GwasSubmitInput) => gwasApi.submit(data),
    onError: (err: Error) => setSubmitError(err.message),
    onSuccess: (jobs) => {
      setSubmitError(null)
      if (jobs.length === 1 && jobs[0].id) {
        navigate({ to: '/gwas/$jobId', params: { jobId: String(jobs[0].id) } })
      } else if (jobs.length > 1) {
        // multi-trait fan-out: stay on page; the recent-jobs table will show them all.
        setSelectedTraits(new Set())
      }
    },
  })

  function toggleTrait(id: string) {
    setSelectedTraits((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const traitIds = Array.from(selectedTraits)
  const canSubmit =
    !!studyId && !!experimentId && !!datasetId && traitIds.length > 0 && !submitMutation.isPending &&
    (model !== 'mvlmm' || traitIds.length >= 2)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    const payload: GwasSubmitInput = {
      study_id: studyId as ID,
      experiment_id: experimentId as ID,
      dataset_id: datasetId as ID,
      model,
      lmm_test: lmmTest,
      n_pcs: nPcs,
      phenotype_agg: phenotypeAgg,
      qc: { maf, geno, mind, hwe },
      ...(model === 'mvlmm'
        ? { trait_ids: traitIds as ID[] }
        : traitIds.length === 1
          ? { trait_id: traitIds[0] as ID }
          : { trait_ids: traitIds as ID[] }),
    }
    submitMutation.mutate(payload)
  }

  return (
    <div>
      <PageHeader
        title="GWAS Analysis"
        description="Run a genome-wide association study against genotype + phenotype data already in the database."
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Source data */}
        <section className="rounded-md border p-5 space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Source data
          </h2>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium mb-1">Experiment</label>
              <Select
                data-testid="gwas-experiment-select"
                value={experimentId}
                onChange={(e) => {
                  setExperimentId(e.target.value)
                  setDatasetId('')
                  setSelectedTraits(new Set())
                }}
              >
                <option value="">— select an experiment —</option>
                {experiments?.map((exp) => (
                  <option key={String(exp.id)} value={String(exp.id)}>
                    {exp.experiment_name}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Genotyping study</label>
              <Select
                data-testid="gwas-study-select"
                value={studyId}
                onChange={(e) => setStudyId(e.target.value)}
              >
                <option value="">— select a study —</option>
                {studies?.map((s) => (
                  <option key={String(s.id)} value={String(s.id)}>
                    {s.study_name}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Trait dataset</label>
              <Select
                data-testid="gwas-dataset-select"
                value={datasetId}
                onChange={(e) => {
                  setDatasetId(e.target.value)
                  setSelectedTraits(new Set())
                }}
                disabled={!experimentId}
              >
                <option value="">
                  {experimentId ? '— select a dataset —' : 'pick an experiment first'}
                </option>
                {datasets?.map((d) => (
                  <option key={String(d.id)} value={String(d.id)}>
                    {d.dataset_name}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Traits{' '}
                <span className="text-xs text-muted-foreground">
                  ({selectedTraits.size} selected{model === 'mvlmm' && ', ≥2 required'})
                </span>
              </label>
              <div
                data-testid="gwas-trait-list"
                className="max-h-48 overflow-y-auto rounded-md border p-2 text-sm"
              >
                {!datasetId && (
                  <p className="text-muted-foreground">Pick a dataset first</p>
                )}
                {datasetId && (!traits || traits.length === 0) && (
                  <p className="text-muted-foreground">No traits in this dataset</p>
                )}
                {traits?.map((t) => {
                  const id = String(t.id)
                  return (
                    <label
                      key={id}
                      className="flex items-center gap-2 py-1 cursor-pointer hover:bg-muted rounded px-1"
                    >
                      <input
                        type="checkbox"
                        data-testid={`gwas-trait-checkbox-${t.trait_name}`}
                        checked={selectedTraits.has(id)}
                        onChange={() => toggleTrait(id)}
                      />
                      <span>{t.trait_name}</span>
                      {t.trait_units && (
                        <span className="text-xs text-muted-foreground">
                          ({t.trait_units})
                        </span>
                      )}
                    </label>
                  )
                })}
              </div>
            </div>
          </div>
        </section>

        {/* Model */}
        <section className="rounded-md border p-5 space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Model
          </h2>

          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="block text-sm font-medium mb-1">Association model</label>
              <Select
                data-testid="gwas-model-select"
                value={model}
                onChange={(e) => setModel(e.target.value as Model)}
              >
                <option value="lmm">Linear mixed model (LMM) — kinship only</option>
                <option value="mvlmm">Multi-trait LMM (mvLMM) — requires ≥2 traits</option>
                <option value="bslmm">Bayesian sparse LMM (BSLMM)</option>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">LMM test</label>
              <Select
                data-testid="gwas-lmm-test-select"
                value={lmmTest}
                onChange={(e) => setLmmTest(e.target.value as LmmTest)}
                disabled={model !== 'lmm'}
              >
                <option value="wald">Wald</option>
                <option value="lrt">LRT</option>
                <option value="score">Score</option>
                <option value="all">All three</option>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                PC covariates <span className="text-xs text-muted-foreground">({nPcs})</span>
              </label>
              <input
                data-testid="gwas-npcs-slider"
                type="range"
                min={0}
                max={10}
                step={1}
                value={nPcs}
                onChange={(e) => setNPcs(Number(e.target.value))}
                className="w-full"
              />
            </div>
          </div>
        </section>

        {/* Advanced (collapsible) */}
        <section className="rounded-md border p-5 space-y-4">
          <button
            data-testid="gwas-advanced-toggle"
            type="button"
            onClick={() => setShowAdvanced((v) => !v)}
            className="flex items-center gap-1 text-sm font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground"
          >
            {showAdvanced ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            QC thresholds &amp; aggregation
          </button>
          {showAdvanced && (
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="block text-sm font-medium mb-1">Min MAF</label>
                <Input
                  data-testid="gwas-qc-maf"
                  type="number"
                  step="0.01"
                  min="0"
                  max="0.5"
                  value={maf}
                  onChange={(e) => setMaf(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Max variant missing rate
                </label>
                <Input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={geno}
                  onChange={(e) => setGeno(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Max sample missing rate
                </label>
                <Input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={mind}
                  onChange={(e) => setMind(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">HWE p-value min</label>
                <Input
                  type="number"
                  step="1e-6"
                  min="0"
                  max="1"
                  value={hwe}
                  onChange={(e) => setHwe(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Phenotype aggregation (per accession)
                </label>
                <Select value={phenotypeAgg} onChange={(e) => setPhenotypeAgg(e.target.value as Agg)}>
                  <option value="mean">Mean</option>
                  <option value="median">Median</option>
                  <option value="first">First observation</option>
                </Select>
              </div>
            </div>
          )}
        </section>

        {submitError && (
          <div className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
            {submitError}
          </div>
        )}

        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {model === 'mvlmm' && traitIds.length >= 2 && (
              <>Will run 1 joint mvLMM job across {traitIds.length} traits.</>
            )}
            {model !== 'mvlmm' && traitIds.length > 1 && (
              <>Will fan out into {traitIds.length} independent {model.toUpperCase()} jobs.</>
            )}
            {traitIds.length === 1 && <>Will run 1 {model.toUpperCase()} job.</>}
          </p>
          <Button data-testid="gwas-submit" type="submit" disabled={!canSubmit}>
            <Play className="mr-2 h-4 w-4" />
            {submitMutation.isPending ? 'Submitting…' : 'Run GWAS'}
          </Button>
        </div>
      </form>

      {/* Recent runs */}
      <section className="mt-10">
        <h2 className="text-lg font-semibold mb-3">Recent GWAS runs</h2>
        {!recentJobs || recentJobs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No runs yet.</p>
        ) : (
          <div className="rounded-md border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr className="text-left">
                  <th className="px-3 py-2 font-medium">Job ID</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Progress</th>
                  <th className="px-3 py-2 font-medium">Created</th>
                  <th className="px-3 py-2 font-medium">Stage</th>
                </tr>
              </thead>
              <tbody>
                {recentJobs.map((job) => {
                  const id = String(job.id)
                  const stage =
                    job.progress_detail && typeof job.progress_detail === 'object'
                      ? String((job.progress_detail as Record<string, unknown>).stage ?? '')
                      : ''
                  return (
                    <tr
                      key={id}
                      onClick={() => navigate({ to: '/gwas/$jobId', params: { jobId: id } })}
                      className="cursor-pointer border-t hover:bg-muted/30"
                    >
                      <td className="px-3 py-2 font-mono text-xs">{id.slice(0, 8)}…</td>
                      <td className="px-3 py-2">
                        <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
                      </td>
                      <td className="px-3 py-2">{Math.round((job.progress ?? 0) * 100)}%</td>
                      <td className="px-3 py-2">{job.created_at ?? '—'}</td>
                      <td className="px-3 py-2 text-muted-foreground">{stage || '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

export const Route = createFileRoute('/gwas/')({ component: GwasLanding })
