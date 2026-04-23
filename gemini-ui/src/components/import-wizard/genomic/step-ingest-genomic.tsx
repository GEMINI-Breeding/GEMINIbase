import { useEffect, useRef, useState } from 'react'
import type { FileWithPath } from '@/components/upload/dropzone'
import type { DetectionResult } from '@/components/import-wizard/detection-engine'
import type {
  GenomicMetadata,
  SampleResolution,
  IngestResult,
} from '@/components/import-wizard/genomic/genomic-wizard'
import type { GenotypeMatrixVariantRow } from '@/api/types'
import { genotypingStudiesApi } from '@/api/endpoints/genotyping-studies'
import { accessionsApi } from '@/api/endpoints/accessions'
import { experimentsApi } from '@/api/endpoints/experiments'
import { populationsApi } from '@/api/endpoints/populations'
import { parseMatrixFile } from '@/lib/genomic-matrix-parser'
import { parseHapmapFile, readHapmapSampleHeaders } from '@/lib/hapmap-parser'
import { parseVcfFile, readVcfSampleHeaders } from '@/lib/vcf-parser'
import { useUpload } from '@/hooks/use-upload'
import { UploadProgress } from '@/components/upload/upload-progress'
import { Button } from '@/components/ui/button'
import { Loader2, CheckCircle, AlertTriangle } from 'lucide-react'

type Phase =
  | 'setup'
  | 'creating-accessions'
  | 'uploading-file'
  | 'ingesting'
  | 'done'
  | 'error'

interface StepIngestGenomicProps {
  detection: DetectionResult
  file: FileWithPath
  metadata: GenomicMetadata
  resolution: SampleResolution
  onNext: (result: IngestResult) => void
  onBack: () => void
}

interface Progress {
  variantsInserted: number
  recordsInserted: number
  rowsProcessed: number
  totalRows: number | null
  batchesRun: number
  errors: string[]
}

const EMPTY_PROGRESS: Progress = {
  variantsInserted: 0,
  recordsInserted: 0,
  rowsProcessed: 0,
  totalRows: null,
  batchesRun: 0,
  errors: [],
}

const INGEST_BATCH_SIZE = 500

export function StepIngestGenomic({
  detection,
  file,
  metadata,
  resolution,
  onNext,
  onBack,
}: StepIngestGenomicProps) {
  const [phase, setPhase] = useState<Phase>('setup')
  const [progress, setProgress] = useState<Progress>(EMPTY_PROGRESS)
  const [studyId, setStudyId] = useState<string | null>(metadata.studyId)
  const [rawObjectName, setRawObjectName] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const startedRef = useRef(false)
  const abortRef = useRef(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  const { state: uploadState, startUpload } = useUpload()

  // Main orchestration — runs exactly once on mount.
  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    abortControllerRef.current = new AbortController()
    const signal = abortControllerRef.current.signal

    async function run() {
      try {
        // -- Create experiment if the user asked us to ----------------
        if (metadata.createNewExperiment && metadata.experimentName) {
          try {
            await experimentsApi.create({ experiment_name: metadata.experimentName })
          } catch {
            // An experiment with this name may already exist — safe to
            // proceed; the study create call below resolves by name.
          }
        }

        // -- Create or fetch study ------------------------------------
        let resolvedStudyId = studyId
        let resolvedStudyName = metadata.studyName
        if (!resolvedStudyId) {
          const created = await genotypingStudiesApi.create({
            study_name: metadata.studyName,
            ...(metadata.experimentName ? { experiment_name: metadata.experimentName } : {}),
          })
          resolvedStudyId = created.id ?? null
          resolvedStudyName = created.study_name ?? metadata.studyName
        }
        if (!resolvedStudyId) {
          throw new Error('Could not resolve study id after create')
        }
        setStudyId(resolvedStudyId)

        // -- Ensure a population for this study's panel, linked to the
        //    experiment. Accessions we create below are attached to it so
        //    experiment-cascade-delete reaches them via the
        //    experiment → population → accession path. Without this the
        //    wizard's auto-created accessions end up orphaned (bug seen
        //    when deleting an experiment left all its imported samples
        //    behind). Population name tracks the study so repeated
        //    imports into the same experiment stay distinct per panel.
        let populationName: string | null = null
        if (metadata.experimentName && resolution.createdAccessions.length > 0) {
          populationName = resolvedStudyName
          try {
            await populationsApi.create({
              population_name: populationName,
              experiment_name: metadata.experimentName,
            })
          } catch {
            // Already exists — Population.create is idempotent via
            // get_or_create on the server.
          }
        }

        // -- Create accessions the user asked us to auto-create -------
        if (resolution.createdAccessions.length > 0) {
          setPhase('creating-accessions')
          for (const name of resolution.createdAccessions) {
            if (signal.aborted) return
            try {
              await accessionsApi.create({
                accession_name: name,
                ...(populationName ? { population_name: populationName } : {}),
              })
            } catch {
              // Accession may already exist; safe to ignore — ingest will
              // look it up by name anyway.
            }
          }
        }

        // -- Upload raw file to MinIO ---------------------------------
        setPhase('uploading-file')
        const objectName = `Raw/genomic/${sanitize(resolvedStudyName)}/${file.name}`
        setRawObjectName(objectName)
        await startUpload([{ file, objectName }])
        if (signal.aborted) return

        // -- Ingest variant rows in batches ---------------------------
        setPhase('ingesting')

        const sampleHeaders = await resolveSampleHeaders(detection, file)
        // Map each sample-header index → canonical accession name. Headers
        // the user opted to skip get filtered out entirely before ingest.
        const keptIndices: number[] = []
        const batchSampleHeaders: string[] = []
        sampleHeaders.forEach((h, i) => {
          if (resolution.skippedHeaders.has(h)) return
          const canonical = resolution.canonicalByHeader[h]
          if (!canonical) return
          keptIndices.push(i)
          batchSampleHeaders.push(canonical)
        })
        const droppedIndices = new Set<number>(
          sampleHeaders.map((_, i) => i).filter((i) => !keptIndices.includes(i)),
        )

        let cumulativeRows = 0
        const parser = buildParser(detection, file, droppedIndices, signal)

        for await (const batch of parser) {
          if (signal.aborted) return
          cumulativeRows = batch.cumulativeRows
          // Each variant row already has calls filtered to keptIndices
          // thanks to `skippedSampleIndices` passed into the parser.
          const res = await genotypingStudiesApi.ingestMatrix(resolvedStudyId, {
            sample_headers: batchSampleHeaders,
            variant_rows: batch.rows as GenotypeMatrixVariantRow[],
          })
          setProgress((prev) => ({
            variantsInserted: prev.variantsInserted + (res.variants_inserted ?? 0),
            recordsInserted: prev.recordsInserted + (res.records_inserted ?? 0),
            rowsProcessed: cumulativeRows,
            totalRows: batch.totalRows,
            batchesRun: prev.batchesRun + 1,
            errors: res.errors && res.errors.length > 0
              ? [...prev.errors, ...res.errors]
              : prev.errors,
          }))
        }

        setPhase('done')
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Ingest failed'
        setErrorMessage(msg)
        setPhase('error')
      }
    }

    run()
    // Do not abort from an effect cleanup — React 19 StrictMode double-
    // invokes mount/cleanup in dev, and aborting the first run means
    // nothing ever completes. The user-initiated Abort button is still
    // wired via `handleAbort` below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleContinue() {
    if (!studyId) return
    onNext({
      studyId,
      studyName: metadata.studyName,
      variantsInserted: progress.variantsInserted,
      recordsInserted: progress.recordsInserted,
      batchesRun: progress.batchesRun,
      errors: progress.errors,
      rawObjectName,
    })
  }

  function handleAbort() {
    abortRef.current = true
    abortControllerRef.current?.abort()
  }

  const isComplete = phase === 'done'

  return (
    <div className="space-y-6">
      <div className="rounded-lg border p-4 space-y-3" data-testid="genomic-ingest-status">
        <h3 className="font-medium">Ingesting {file.name}</h3>
        <div className="space-y-2 text-sm">
          <PhaseRow label="Create / fetch study" done={phase !== 'setup'} active={phase === 'setup'} />
          <PhaseRow
            label={`Create ${resolution.createdAccessions.length} accession${resolution.createdAccessions.length === 1 ? '' : 's'}`}
            done={['uploading-file', 'ingesting', 'done'].includes(phase)}
            active={phase === 'creating-accessions'}
            skipped={resolution.createdAccessions.length === 0}
          />
          <PhaseRow
            label="Upload raw file"
            done={['ingesting', 'done'].includes(phase)}
            active={phase === 'uploading-file'}
          />
          <PhaseRow label="Ingest variant records" done={phase === 'done'} active={phase === 'ingesting'} />
        </div>
      </div>

      {uploadState.files.length > 0 && (
        <div className="rounded-lg border p-4">
          <h3 className="font-medium mb-3">File Upload</h3>
          <UploadProgress state={uploadState} />
        </div>
      )}

      {(phase === 'ingesting' || phase === 'done') && (
        <div className="rounded-lg border p-4 space-y-3" data-testid="genomic-ingest-progress">
          <h3 className="font-medium">Record Ingestion</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <Stat label="Variants inserted" value={progress.variantsInserted} />
            <Stat label="Genotype records inserted" value={progress.recordsInserted} />
            <Stat label="Batches sent" value={progress.batchesRun} />
          </div>
          {progress.totalRows !== null && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Rows processed</span>
                <span className="tabular-nums">
                  {progress.rowsProcessed.toLocaleString()} / {progress.totalRows.toLocaleString()}
                </span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className="bg-primary h-2 rounded-full transition-all"
                  style={{
                    width: `${progress.totalRows > 0 ? (progress.rowsProcessed / progress.totalRows) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>
          )}
          {progress.errors.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-muted-foreground">
                {progress.errors.length} server-side warning{progress.errors.length === 1 ? '' : 's'}
              </summary>
              <ul className="mt-2 list-disc pl-5 space-y-0.5 max-h-32 overflow-y-auto">
                {progress.errors.slice(0, 50).map((e, i) => (
                  <li key={i} className="text-xs">{e}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {phase === 'error' && errorMessage && (
        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-4 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-destructive shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium text-destructive">Ingest failed</p>
            <p className="text-destructive/80">{errorMessage}</p>
          </div>
        </div>
      )}

      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={phase === 'error' ? onBack : handleAbort}
          disabled={isComplete}
        >
          {phase === 'error' ? 'Back' : isComplete ? 'Back' : 'Abort'}
        </Button>
        <Button onClick={handleContinue} disabled={!isComplete} data-testid="genomic-ingest-continue">
          Continue
        </Button>
      </div>
    </div>
  )
}

function PhaseRow({
  label,
  done,
  active,
  skipped,
}: {
  label: string
  done: boolean
  active: boolean
  skipped?: boolean
}) {
  if (skipped) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <div className="w-4 h-4 rounded-full border border-muted-foreground" />
        <span>{label} (skipped)</span>
      </div>
    )
  }
  return (
    <div className="flex items-center gap-2">
      {done ? (
        <CheckCircle className="w-4 h-4 text-green-600 shrink-0" />
      ) : active ? (
        <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />
      ) : (
        <div className="w-4 h-4 rounded-full border border-muted-foreground shrink-0" />
      )}
      <span className={done ? '' : active ? 'font-medium' : 'text-muted-foreground'}>{label}</span>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold tabular-nums">{value.toLocaleString()}</div>
    </div>
  )
}

function sanitize(s: string): string {
  return s.trim().replace(/[^\w.-]+/g, '_') || 'genomic'
}

async function resolveSampleHeaders(
  detection: DetectionResult,
  file: FileWithPath,
): Promise<string[]> {
  const shape = detection.genomicShape!
  if (shape.sampleHeaders.length > 0) return shape.sampleHeaders
  if (shape.format === 'hapmap') return readHapmapSampleHeaders(file as unknown as File)
  if (shape.format === 'vcf') return readVcfSampleHeaders(file as unknown as File)
  return []
}

function buildParser(
  detection: DetectionResult,
  file: FileWithPath,
  skippedSampleIndices: Set<number>,
  signal: AbortSignal,
) {
  const shape = detection.genomicShape!
  const f = file as unknown as File
  const opts = { batchSize: INGEST_BATCH_SIZE, skippedSampleIndices, signal }
  if (shape.format === 'hapmap') return parseHapmapFile(f, opts)
  if (shape.format === 'vcf') return parseVcfFile(f, opts)
  return parseMatrixFile(f, shape, opts)
}
