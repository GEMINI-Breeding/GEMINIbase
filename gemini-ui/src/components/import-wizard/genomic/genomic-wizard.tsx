import { useCallback, useMemo, useState } from 'react'
import type { FileWithPath } from '@/components/upload/dropzone'
import type { DetectionResult } from '@/components/import-wizard/detection-engine'
import { StepMetadataGenomic } from '@/components/import-wizard/genomic/step-metadata-genomic'
import { StepSampleResolve } from '@/components/import-wizard/genomic/step-sample-resolve'
import { StepIngestGenomic } from '@/components/import-wizard/genomic/step-ingest-genomic'
import { StepConfirmGenomic } from '@/components/import-wizard/genomic/step-confirm-genomic'
import { cn } from '@/lib/utils'
import { FileText, Users, Upload, CheckCircle } from 'lucide-react'

export interface GenomicMetadata {
  studyId: string | null
  studyName: string
  createNewStudy: boolean
  experimentName: string | null
}

export interface SampleResolution {
  /** Raw sample header → canonical accession name used at ingest time. */
  canonicalByHeader: Record<string, string>
  /** Raw sample headers that should be dropped from the ingest payload. */
  skippedHeaders: Set<string>
  /** Newly-created accession names (surfaced on the confirm page). */
  createdAccessions: string[]
}

export interface IngestResult {
  studyId: string
  studyName: string
  variantsInserted: number
  recordsInserted: number
  batchesRun: number
  errors: string[]
  rawObjectName: string | null
}

interface GenomicWizardProps {
  files: FileWithPath[]
  detection: DetectionResult
  onExit: () => void
}

const STEPS = [
  { label: 'Metadata', icon: FileText },
  { label: 'Samples', icon: Users },
  { label: 'Ingest', icon: Upload },
  { label: 'Confirm', icon: CheckCircle },
] as const

export function GenomicWizard({ files, detection, onExit }: GenomicWizardProps) {
  const [step, setStep] = useState(0)
  const [metadata, setMetadata] = useState<GenomicMetadata | null>(null)
  const [resolution, setResolution] = useState<SampleResolution | null>(null)
  const [ingestResult, setIngestResult] = useState<IngestResult | null>(null)

  const genomicFile = detection.genomicFile ?? files[0] ?? null
  const shape = detection.genomicShape

  const handleMetadataNext = useCallback((m: GenomicMetadata) => {
    setMetadata(m)
    setStep(1)
  }, [])

  const handleResolveNext = useCallback((r: SampleResolution) => {
    setResolution(r)
    setStep(2)
  }, [])

  const handleIngestNext = useCallback((result: IngestResult) => {
    setIngestResult(result)
    setStep(3)
  }, [])

  const handleBack = useCallback((toStep: number) => setStep(toStep), [])

  const isPlink = shape?.format === 'plink'

  const content = useMemo(() => {
    if (!shape || !genomicFile) {
      return (
        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive">
          Could not identify the genomic layout of the uploaded file. Go back and
          try a different file.
        </div>
      )
    }

    if (isPlink) {
      return (
        <div className="rounded-md border p-6 space-y-3">
          <h3 className="text-lg font-semibold">PLINK import not yet supported</h3>
          <p className="text-sm text-muted-foreground">
            PLINK <code>.ped/.map/.bed/.bim/.fam</code> files are recognized,
            but ingest hasn't been wired up yet. Use HapMap (<code>.hmp.txt</code>),
            VCF (<code>.vcf</code>), or an xlsx/csv matrix for now.
          </p>
          <div className="pt-2">
            <button
              type="button"
              onClick={onExit}
              className="text-sm underline text-primary"
              data-testid="genomic-plink-exit"
            >
              Back to detect
            </button>
          </div>
        </div>
      )
    }

    if (step === 0) {
      return (
        <StepMetadataGenomic
          detection={detection}
          initial={metadata}
          onNext={handleMetadataNext}
          onBack={onExit}
        />
      )
    }
    if (step === 1 && metadata) {
      return (
        <StepSampleResolve
          detection={detection}
          file={genomicFile}
          metadata={metadata}
          initial={resolution}
          onNext={handleResolveNext}
          onBack={() => handleBack(0)}
        />
      )
    }
    if (step === 2 && metadata && resolution) {
      return (
        <StepIngestGenomic
          detection={detection}
          file={genomicFile}
          metadata={metadata}
          resolution={resolution}
          onNext={handleIngestNext}
          onBack={() => handleBack(1)}
        />
      )
    }
    if (step === 3 && ingestResult) {
      return <StepConfirmGenomic result={ingestResult} onDone={onExit} />
    }
    return null
  }, [
    shape,
    genomicFile,
    isPlink,
    step,
    detection,
    metadata,
    resolution,
    ingestResult,
    handleMetadataNext,
    handleResolveNext,
    handleIngestNext,
    handleBack,
    onExit,
  ])

  return (
    <div className="space-y-6" data-testid="genomic-wizard">
      <nav className="flex items-center justify-center gap-2">
        {STEPS.map((s, i) => {
          const Icon = s.icon
          const isActive = i === step
          const isComplete = i < step
          return (
            <div key={s.label} className="flex items-center">
              {i > 0 && (
                <div
                  className={cn(
                    'w-12 h-px mx-2',
                    isComplete ? 'bg-primary' : 'bg-border',
                  )}
                />
              )}
              <div
                className={cn(
                  'flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors',
                  isActive && 'bg-primary text-primary-foreground',
                  isComplete && 'bg-primary/10 text-primary',
                  !isActive && !isComplete && 'text-muted-foreground',
                )}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{s.label}</span>
                <span className="sm:hidden">{i + 1}</span>
              </div>
            </div>
          )
        })}
      </nav>
      {content}
    </div>
  )
}
