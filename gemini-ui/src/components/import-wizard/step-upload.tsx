import { useState, useEffect, useRef } from 'react'
import type { FileWithPath } from '@/components/upload/dropzone'
import type { DetectionResult } from '@/components/import-wizard/detection-engine'
import type { ImportMetadata, UploadResults, ColumnMapping } from '@/components/import-wizard/wizard-shell'
import { useUpload } from '@/hooks/use-upload'
import { UploadProgress } from '@/components/upload/upload-progress'
import { Button } from '@/components/ui/button'
import { experimentsApi } from '@/api/endpoints/experiments'
import { seasonsApi } from '@/api/endpoints/seasons'
import { sitesApi } from '@/api/endpoints/sites'
import { sensorPlatformsApi } from '@/api/endpoints/sensor-platforms'
import { sensorsApi } from '@/api/endpoints/sensors'
import { datasetsApi } from '@/api/endpoints/datasets'
import { traitsApi } from '@/api/endpoints/traits'
import { Loader2, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'

interface StepUploadProps {
  files: FileWithPath[]
  detection: DetectionResult
  metadata: ImportMetadata
  columnMapping?: ColumnMapping | null
  onNext: (results: UploadResults) => void
  onBack: () => void
}

interface CreationStep {
  type: string
  name: string
  status: 'pending' | 'creating' | 'done' | 'skipped' | 'error'
  id?: string
  error?: string
}

interface IngestionProgress {
  /** Total records emitted across every sheet × trait. */
  total: number
  /** Records successfully POSTed so far. */
  current: number
  /** Which sheet/trait is currently being ingested (for the status line). */
  currentSheet: string | null
  currentTrait: string | null
  /** Per-trait totals, keyed by "sheetName::traitName". */
  perTraitTotal: Map<string, number>
  perTraitCurrent: Map<string, number>
}

export function StepUpload({ files, detection, metadata, columnMapping, onNext, onBack }: StepUploadProps) {
  const [creationSteps, setCreationSteps] = useState<CreationStep[]>([])
  const [phase, setPhase] = useState<'creating' | 'uploading' | 'ingesting' | 'done' | 'error'>('creating')
  const [ingestionProgress, setIngestionProgress] = useState<IngestionProgress>({
    total: 0,
    current: 0,
    currentSheet: null,
    currentTrait: null,
    perTraitTotal: new Map(),
    perTraitCurrent: new Map(),
  })
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const abortedRef = useRef(false)
  const startedRef = useRef(false)
  const phaseRef = useRef<typeof phase>('creating')
  const stepsRef = useRef<CreationStep[]>([])

  // Wrap setPhase to also update the ref
  function updatePhase(p: typeof phase) {
    phaseRef.current = p
    setPhase(p)
  }

  const pendingIngestionRef = useRef(false)

  const { state: uploadState, startUpload, abort: abortUpload } = useUpload({
    onAllComplete: () => {
      if (columnMapping && columnMapping.recordType === 'trait') {
        pendingIngestionRef.current = true
        updatePhase('ingesting')
      } else {
        updatePhase('done')
      }
    },
  })

  // On remount (StrictMode), if the run already completed, restore state from refs
  useEffect(() => {
    if (startedRef.current && phaseRef.current !== 'creating') {
      setPhase(phaseRef.current)
      setCreationSteps([...stepsRef.current])
    }
  }, [])

  // Ingest trait records after file upload completes
  useEffect(() => {
    if (phase !== 'ingesting' || !pendingIngestionRef.current) return
    pendingIngestionRef.current = false

    async function ingestRecords() {
      if (!columnMapping || columnMapping.recordType !== 'trait') {
        updatePhase('done')
        return
      }
      try {
        const { sheets, sheetConfigs } = columnMapping

        // Resolve/create trait entities. Cache by trait name so the same trait
        // appearing on multiple sheets only gets one Trait entity.
        const traitIdCache = new Map<string, string>()
        async function resolveTraitId(name: string): Promise<string> {
          const cached = traitIdCache.get(name)
          if (cached) return cached
          let traitId: string | undefined
          try {
            const existing = await traitsApi.search({ trait_name: name })
            if (existing.length > 0) traitId = existing[0].id
          } catch {
            // search failed (e.g. 404) — fall through to create
          }
          if (!traitId) {
            const created = await traitsApi.create({
              trait_name: name,
              trait_level_id: 0 as unknown as string,
              experiment_name: metadata.experimentName,
            })
            traitId = created.id
          }
          if (!traitId) throw new Error(`Failed to resolve trait ID for "${name}"`)
          traitIdCache.set(name, traitId)
          return traitId
        }

        // Pre-compute per-(sheet, trait) totals so the progress UI can show
        // running totals without waiting until the end. A cell counts only if
        // both the trait value AND plot_number are present and numeric.
        const perTraitTotal = new Map<string, number>()
        let grandTotal = 0
        for (let si = 0; si < sheets.length; si++) {
          const sheet = sheets[si]
          const config = sheetConfigs[si]
          if (!config || !config.plotNumberColumn) continue
          const enabledTraits = config.traitColumns.filter((tc) => tc.enabled)
          for (const trait of enabledTraits) {
            let count = 0
            for (const row of sheet.rows) {
              const raw = row[trait.columnHeader]
              if (raw == null || raw === '') continue
              if (Number.isNaN(Number(raw))) continue
              const plotRaw = row[config.plotNumberColumn]
              if (plotRaw == null || plotRaw === '') continue
              if (Number.isNaN(Number(plotRaw))) continue
              count++
            }
            const key = `${sheet.name}::${trait.traitName}`
            perTraitTotal.set(key, count)
            grandTotal += count
          }
        }

        setIngestionProgress({
          total: grandTotal,
          current: 0,
          currentSheet: null,
          currentTrait: null,
          perTraitTotal,
          perTraitCurrent: new Map(),
        })

        const BATCH_SIZE = 500
        const now = new Date()
        let tsOffset = 0 // monotonically increasing so auto-generated timestamps stay unique across sheets/traits
        let runningCurrent = 0
        const perTraitCurrent = new Map<string, number>()

        for (let si = 0; si < sheets.length; si++) {
          if (abortedRef.current) return
          const sheet = sheets[si]
          const config = sheetConfigs[si]
          // Plot number is the required row identifier — skip sheets that
          // somehow got here without one (wizard validation should prevent it).
          if (!config || !config.plotNumberColumn) continue

          const enabledTraits = config.traitColumns.filter((tc) => tc.enabled)
          for (const trait of enabledTraits) {
            if (abortedRef.current) return
            const traitKey = `${sheet.name}::${trait.traitName}`
            setIngestionProgress((prev) => ({
              ...prev,
              currentSheet: sheet.name,
              currentTrait: trait.traitName,
            }))

            const traitId = await resolveTraitId(trait.traitName)

            // Build all valid records for this (sheet, trait) pair
            const records: Record<string, unknown>[] = []
            for (const row of sheet.rows) {
              const raw = row[trait.columnHeader]
              if (raw == null || raw === '') continue
              const value = Number(raw)
              if (Number.isNaN(value)) continue

              // Plot number is required and must be numeric.
              const plotRaw = row[config.plotNumberColumn]
              if (plotRaw == null || plotRaw === '') continue
              const plotNumber = Number(plotRaw)
              if (Number.isNaN(plotNumber)) continue

              const record: Record<string, unknown> = {
                trait_value: value,
                plot_number: plotNumber,
              }

              if (config.plotRowColumn && row[config.plotRowColumn] != null) {
                const v = Number(row[config.plotRowColumn])
                if (!Number.isNaN(v)) record.plot_row_number = v
              }
              if (config.plotColumnColumn && row[config.plotColumnColumn] != null) {
                const v = Number(row[config.plotColumnColumn])
                if (!Number.isNaN(v)) record.plot_column_number = v
              }

              // Build record_info: sheet name, source column, optional
              // genotype, and any user-selected metadata columns.
              const recordInfo: Record<string, unknown> = {
                sheet: sheet.name,
                source_column: trait.columnHeader,
              }
              if (config.genotypeColumn) {
                const gv = row[config.genotypeColumn]
                recordInfo.genotype = gv != null ? String(gv) : null
              }
              for (const mc of config.metadataColumns) {
                const v = row[mc.columnHeader]
                recordInfo[mc.label] = v != null ? v : null
              }
              record.record_info = recordInfo

              if (config.timestampColumn && row[config.timestampColumn] != null) {
                record.timestamp = String(row[config.timestampColumn])
              } else {
                record.timestamp = new Date(now.getTime() + tsOffset * 1000).toISOString()
              }
              tsOffset++

              records.push(record)
            }

            // POST in batches
            for (let offset = 0; offset < records.length; offset += BATCH_SIZE) {
              if (abortedRef.current) return
              const batch = records.slice(offset, offset + BATCH_SIZE)
              await traitsApi.bulkCreateRecords(traitId, {
                records: batch,
                experiment_name: metadata.experimentName,
                season_name: metadata.seasonName,
                site_name: metadata.siteName,
                dataset_name: metadata.datasetNames[0] || undefined,
              })
              runningCurrent += batch.length
              perTraitCurrent.set(
                traitKey,
                (perTraitCurrent.get(traitKey) || 0) + batch.length,
              )
              setIngestionProgress((prev) => ({
                ...prev,
                current: runningCurrent,
                currentSheet: sheet.name,
                currentTrait: trait.traitName,
                perTraitCurrent: new Map(perTraitCurrent),
              }))
            }
          }
        }

        updatePhase('done')
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Record ingestion failed'
        setErrorMessage(msg)
        updatePhase('error')
      }
    }

    ingestRecords()
  }, [phase]) // eslint-disable-line react-hooks/exhaustive-deps

  // Build the file-to-object-name map
  function buildFileMap(experimentName: string) {
    return files.map((file) => {
      const path = file.path || file.name
      // Extract date from path for organization
      const dateMatch = path.match(/(\d{4}-\d{2}-\d{2})/)
      const date = dateMatch ? dateMatch[1] : 'unsorted'
      const objectName = `Raw/${experimentName}/${date}/${file.name}`
      return { file, objectName }
    })
  }

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true

    // Idempotent create: if entity already exists (e.g., from StrictMode double-mount),
    // fetch the existing one by name instead of failing.
    async function createOrGet<T extends { id?: string }>(
      createFn: () => Promise<T>,
      searchFn: () => Promise<T[]>,
    ): Promise<T> {
      try {
        return await createFn()
      } catch (createErr) {
        // Entity likely already exists — try to fetch it
        try {
          const existing = await searchFn()
          if (existing.length > 0) return existing[0]
        } catch {
          // Search also failed (e.g., 404 for empty results)
        }
        throw createErr
      }
    }

    async function run() {
      const created: UploadResults['createdEntities'] = []
      let experimentName = metadata.experimentName
      let experimentId = metadata.experimentId

      // Build creation plan
      const steps: CreationStep[] = []
      if (metadata.createNew.experiment) {
        steps.push({ type: 'Experiment', name: metadata.experimentName, status: 'pending' })
      } else {
        steps.push({ type: 'Experiment', name: metadata.experimentName, status: 'skipped', id: metadata.experimentId || undefined })
      }
      if (metadata.createNew.season) {
        steps.push({ type: 'Season', name: metadata.seasonName, status: 'pending' })
      }
      if (metadata.createNew.site) {
        steps.push({ type: 'Site', name: metadata.siteName, status: 'pending' })
      }
      if (metadata.createNew.sensorPlatform) {
        steps.push({ type: 'Sensor Platform', name: metadata.sensorPlatformName, status: 'pending' })
      }
      if (metadata.createNew.sensor) {
        steps.push({ type: 'Sensor', name: metadata.sensorName, status: 'pending' })
      }
      for (const dsName of metadata.datasetNames) {
        steps.push({ type: 'Dataset', name: dsName, status: 'pending' })
      }
      stepsRef.current = [...steps]
      setCreationSteps([...steps])

      function updateStep(index: number, updates: Partial<CreationStep>) {
        steps[index] = { ...steps[index], ...updates }
        stepsRef.current = [...steps]
        setCreationSteps([...steps])
      }

      try {
        let stepIdx = 0

        // Create experiment
        if (metadata.createNew.experiment) {
          if (abortedRef.current) return
          updateStep(stepIdx, { status: 'creating' })
          const exp = await createOrGet(
            () => experimentsApi.create({ experiment_name: metadata.experimentName }),
            () => experimentsApi.search({ experiment_name: metadata.experimentName }),
          )
          experimentId = exp.id || null
          experimentName = exp.experiment_name
          updateStep(stepIdx, { status: 'done', id: exp.id })
          created.push({ type: 'Experiment', name: experimentName, id: exp.id || '' })
        }
        stepIdx++

        // Create season
        if (metadata.createNew.season) {
          if (abortedRef.current) return
          updateStep(stepIdx, { status: 'creating' })
          const season = await createOrGet(
            () => seasonsApi.create({ season_name: metadata.seasonName, experiment_name: experimentName }),
            () => seasonsApi.search({ season_name: metadata.seasonName }),
          )
          updateStep(stepIdx, { status: 'done', id: season.id })
          created.push({ type: 'Season', name: metadata.seasonName, id: season.id || '' })
          stepIdx++
        }

        // Create site
        if (metadata.createNew.site) {
          if (abortedRef.current) return
          updateStep(stepIdx, { status: 'creating' })
          const site = await createOrGet(
            () => sitesApi.create({ site_name: metadata.siteName, experiment_name: experimentName }),
            () => sitesApi.search({ site_name: metadata.siteName }),
          )
          updateStep(stepIdx, { status: 'done', id: site.id })
          created.push({ type: 'Site', name: metadata.siteName, id: site.id || '' })
          stepIdx++
        }

        // Create sensor platform
        if (metadata.createNew.sensorPlatform) {
          if (abortedRef.current) return
          updateStep(stepIdx, { status: 'creating' })
          const sp = await createOrGet(
            () => sensorPlatformsApi.create({ sensor_platform_name: metadata.sensorPlatformName, experiment_name: experimentName }),
            () => sensorPlatformsApi.search({ sensor_platform_name: metadata.sensorPlatformName }),
          )
          updateStep(stepIdx, { status: 'done', id: sp.id })
          created.push({ type: 'Sensor Platform', name: metadata.sensorPlatformName, id: sp.id || '' })
          stepIdx++
        }

        // Create sensor
        if (metadata.createNew.sensor) {
          if (abortedRef.current) return
          updateStep(stepIdx, { status: 'creating' })
          const sensor = await createOrGet(
            () => sensorsApi.create({
              sensor_name: metadata.sensorName,
              sensor_type_id: 0 as unknown as string,
              sensor_data_type_id: 0 as unknown as string,
              sensor_data_format_id: 0 as unknown as string,
              experiment_name: experimentName,
              sensor_platform_name: metadata.sensorPlatformName,
            }),
            () => sensorsApi.search({ sensor_name: metadata.sensorName }),
          )
          updateStep(stepIdx, { status: 'done', id: sensor.id })
          created.push({ type: 'Sensor', name: metadata.sensorName, id: sensor.id || '' })
          stepIdx++
        }

        // Create datasets with file prefix info
        for (let di = 0; di < metadata.datasetNames.length; di++) {
          const dsName = metadata.datasetNames[di]
          if (abortedRef.current) return
          updateStep(stepIdx, { status: 'creating' })

          // Store the experiment-level file prefix so the Files tab can list all uploaded files
          const filesPrefix = `Raw/${experimentName}`

          const ds = await createOrGet(
            () => datasetsApi.create({
              dataset_name: dsName,
              experiment_name: experimentName,
              dataset_info: { files_prefix: `gemini/${filesPrefix}`, bucket: 'gemini' },
            }),
            () => datasetsApi.search({ dataset_name: dsName }),
          )
          updateStep(stepIdx, { status: 'done', id: ds.id })
          created.push({ type: 'Dataset', name: dsName, id: ds.id || '' })
          stepIdx++
        }

        // Upload files
        if (abortedRef.current) return
        updatePhase('uploading')
        const fileMap = buildFileMap(experimentName)
        await startUpload(fileMap)

        // Results will be finalized when onAllComplete fires
        // Store created entities for the results
        createdRef.current = created
        expIdRef.current = experimentId
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'An error occurred'
        setErrorMessage(msg)
        updatePhase('error')

        // Mark current step as error
        const currentIdx = steps.findIndex((s) => s.status === 'creating')
        if (currentIdx >= 0) {
          updateStep(currentIdx, { status: 'error', error: msg })
        }
      }
    }

    run()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const createdRef = useRef<UploadResults['createdEntities']>([])
  const expIdRef = useRef<string | null>(metadata.experimentId)

  function handleContinue() {
    onNext({
      createdEntities: createdRef.current,
      uploadedFiles: uploadState.completedCount,
      failedFiles: uploadState.errorCount,
      experimentId: expIdRef.current,
    })
  }

  function handleAbort() {
    abortedRef.current = true
    abortUpload()
  }

  const isComplete = phase === 'done' && !uploadState.isUploading

  return (
    <div className="space-y-6">
      {/* Entity creation status */}
      <div className="rounded-lg border p-4 space-y-3">
        <h3 className="font-medium">Creating Entities</h3>
        <div className="space-y-2">
          {creationSteps.map((step, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              {step.status === 'done' && <CheckCircle className="w-4 h-4 text-green-600 shrink-0" />}
              {step.status === 'creating' && <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />}
              {step.status === 'pending' && <div className="w-4 h-4 rounded-full border border-muted-foreground shrink-0" />}
              {step.status === 'skipped' && <CheckCircle className="w-4 h-4 text-muted-foreground shrink-0" />}
              {step.status === 'error' && <XCircle className="w-4 h-4 text-destructive shrink-0" />}
              <span className={step.status === 'skipped' ? 'text-muted-foreground' : ''}>
                {step.type}: <span className="font-medium">{step.name}</span>
                {step.status === 'skipped' && ' (existing)'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* File upload progress */}
      {(phase === 'uploading' || phase === 'ingesting' || phase === 'done') && uploadState.files.length > 0 && (
        <div className="rounded-lg border p-4">
          <h3 className="font-medium mb-3">File Upload</h3>
          <UploadProgress state={uploadState} />
        </div>
      )}

      {/* Record ingestion progress */}
      {(phase === 'ingesting' || (phase === 'done' && columnMapping)) && ingestionProgress.total > 0 && (
        <div className="rounded-lg border p-4 space-y-3" data-testid="ingestion-progress">
          <h3 className="font-medium">Record Ingestion</h3>
          <div className="space-y-3">
            {/* Per-trait breakdown */}
            <div className="space-y-1.5 text-sm">
              {[...ingestionProgress.perTraitTotal.entries()].map(([key, total]) => {
                const done = ingestionProgress.perTraitCurrent.get(key) || 0
                const [sheetName, traitName] = key.split('::')
                const isActive =
                  ingestionProgress.currentSheet === sheetName &&
                  ingestionProgress.currentTrait === traitName &&
                  phase === 'ingesting'
                const isFinished = done >= total
                return (
                  <div key={key} className="flex items-center gap-2">
                    {isFinished ? (
                      <CheckCircle className="w-4 h-4 text-green-600 shrink-0" />
                    ) : isActive ? (
                      <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-muted-foreground shrink-0" />
                    )}
                    <span className="text-muted-foreground">{sheetName}</span>
                    <span className="text-muted-foreground">·</span>
                    <span className="font-medium">{traitName}</span>
                    <span className="ml-auto tabular-nums">
                      {done} / {total}
                    </span>
                  </div>
                )
              })}
            </div>
            {/* Overall progress bar */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Overall</span>
                <span className="tabular-nums">
                  {ingestionProgress.current} / {ingestionProgress.total} records
                </span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className="bg-primary h-2 rounded-full transition-all"
                  style={{
                    width: `${ingestionProgress.total > 0 ? (ingestionProgress.current / ingestionProgress.total) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error message */}
      {phase === 'error' && errorMessage && (
        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-4 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-destructive shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium text-destructive">Upload failed</p>
            <p className="text-destructive/80">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={phase === 'error' ? onBack : handleAbort}
          disabled={isComplete}
        >
          {phase === 'error' ? 'Back' : phase === 'creating' || phase === 'uploading' || phase === 'ingesting' ? 'Abort' : 'Back'}
        </Button>
        <Button onClick={handleContinue} disabled={!isComplete} data-testid="upload-continue">
          Continue
        </Button>
      </div>
    </div>
  )
}
