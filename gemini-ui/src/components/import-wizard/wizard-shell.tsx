import { useState, useCallback, useMemo } from 'react'
import type { FileWithPath } from '@/components/upload/dropzone'
import type { DetectionResult } from '@/components/import-wizard/detection-engine'
import type { ParsedSheet } from '@/lib/spreadsheet-parser'
import { StepDetect } from '@/components/import-wizard/step-detect'
import { StepMetadata } from '@/components/import-wizard/step-metadata'
import { StepColumnMapping } from '@/components/import-wizard/step-column-mapping'
import { StepUpload } from '@/components/import-wizard/step-upload'
import { StepConfirm } from '@/components/import-wizard/step-confirm'
import { cn } from '@/lib/utils'
import { Search, FileText, Upload, CheckCircle, TableProperties } from 'lucide-react'

export interface ImportMetadata {
  experimentId: string | null
  experimentName: string
  seasonName: string
  siteName: string
  sensorPlatformName: string
  sensorName: string
  datasetNames: string[]
  createNew: {
    experiment: boolean
    season: boolean
    site: boolean
    sensorPlatform: boolean
    sensor: boolean
  }
}

export interface TraitColumn {
  /** Original header text in the sheet — the key used to look up values in row objects. */
  columnHeader: string
  /** Editable trait label, defaults to columnHeader. Becomes the Trait entity name. */
  traitName: string
  /** Whether this column is currently selected for import. */
  enabled: boolean
}

export interface MetadataColumn {
  /** Original header text in the sheet — the key used to look up values in row objects. */
  columnHeader: string
  /** Label used as the key in record_info. Defaults to columnHeader but editable. */
  label: string
}

export interface SheetMapping {
  sheetName: string
  /** Plot number column — the primary row identifier. Required for the sheet to be valid. */
  plotNumberColumn: string | null
  /** Optional plot row. May only be set if plotNumberColumn is also set. */
  plotRowColumn: string | null
  /** Optional plot column. May only be set if plotNumberColumn is also set. */
  plotColumnColumn: string | null
  /** All trait columns the user has configured (enabled or not — disabled entries preserve label edits). */
  traitColumns: TraitColumn[]
  /** Optional genotype/accession column. Stored passthrough in record_info.genotype. */
  genotypeColumn: string | null
  /** Optional timestamp column. If unmapped, timestamps are auto-generated. */
  timestampColumn: string | null
  /** User-selected free-form metadata columns. Each is dumped into record_info under its label. */
  metadataColumns: MetadataColumn[]
}

export interface ColumnMapping {
  recordType: 'trait' | 'dataset'
  sheets: ParsedSheet[]
  /** One config per sheet, same order as sheets. */
  sheetConfigs: SheetMapping[]
}

export interface UploadResults {
  createdEntities: { type: string; name: string; id: string }[]
  uploadedFiles: number
  failedFiles: number
  experimentId: string | null
}

interface WizardState {
  files: FileWithPath[]
  detection: DetectionResult | null
  metadata: ImportMetadata | null
  columnMapping: ColumnMapping | null
  uploadResults: UploadResults | null
}

const BASE_STEPS = [
  { label: 'Detect', icon: Search },
  { label: 'Metadata', icon: FileText },
  { label: 'Upload', icon: Upload },
  { label: 'Confirm', icon: CheckCircle },
] as const

const MAPPING_STEP = { label: 'Map Columns', icon: TableProperties } as const

export function WizardShell() {
  const [step, setStep] = useState(0)
  const [state, setState] = useState<WizardState>({
    files: [],
    detection: null,
    metadata: null,
    columnMapping: null,
    uploadResults: null,
  })

  const needsMapping = state.detection?.dataCategories.some(c => c === 'csv_tabular') ?? false

  const steps = useMemo(() => {
    if (needsMapping) {
      return [BASE_STEPS[0], BASE_STEPS[1], MAPPING_STEP, BASE_STEPS[2], BASE_STEPS[3]]
    }
    return [...BASE_STEPS]
  }, [needsMapping])

  // Step indices adjust based on whether mapping step is present
  const uploadStepIndex = needsMapping ? 3 : 2
  const confirmStepIndex = needsMapping ? 4 : 3
  const mappingStepIndex = 2 // only used when needsMapping is true

  const handleDetectNext = useCallback((files: FileWithPath[], detection: DetectionResult) => {
    setState((prev) => ({ ...prev, files, detection }))
    setStep(1)
  }, [])

  const handleMetadataNext = useCallback((metadata: ImportMetadata) => {
    setState((prev) => ({ ...prev, metadata }))
    // Step 2 is either the mapping step (for tabular data) or the upload step
    setStep(2)
  }, [])

  const handleMappingNext = useCallback((mapping: ColumnMapping) => {
    setState((prev) => ({ ...prev, columnMapping: mapping }))
    setStep(3) // proceed to upload (index 3 when mapping is present)
  }, [])

  const handleUploadNext = useCallback((results: UploadResults) => {
    setState((prev) => ({ ...prev, uploadResults: results }))
    setStep(needsMapping ? 4 : 3)
  }, [needsMapping])

  const handleDone = useCallback(() => {
    setState({ files: [], detection: null, metadata: null, columnMapping: null, uploadResults: null })
    setStep(0)
  }, [])

  const handleBack = useCallback((toStep: number) => {
    setStep(toStep)
  }, [])

  return (
    <div className="space-y-6" data-testid="import-wizard">
      {/* Step indicator */}
      <nav className="flex items-center justify-center gap-2">
        {steps.map((s, i) => {
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

      {/* Step content */}
      {step === 0 && <StepDetect onNext={handleDetectNext} />}

      {step === 1 && state.detection && (
        <StepMetadata
          detection={state.detection}
          onNext={handleMetadataNext}
          onBack={() => handleBack(0)}
        />
      )}

      {needsMapping && step === mappingStepIndex && state.detection && state.metadata && (
        <StepColumnMapping
          files={state.files}
          onNext={handleMappingNext}
          onBack={() => handleBack(1)}
        />
      )}

      {step === uploadStepIndex && state.detection && state.metadata && (
        <StepUpload
          files={state.files}
          detection={state.detection}
          metadata={state.metadata}
          columnMapping={state.columnMapping}
          onNext={handleUploadNext}
          onBack={() => handleBack(needsMapping ? mappingStepIndex : 1)}
        />
      )}

      {step === confirmStepIndex && state.uploadResults && (
        <StepConfirm results={state.uploadResults} onDone={handleDone} />
      )}
    </div>
  )
}
