import { useState, useCallback, useMemo } from 'react'
import type { FileWithPath } from '@/components/upload/dropzone'
import type { DetectionResult } from '@/components/import-wizard/detection-engine'
import type { ParsedSheet } from '@/lib/spreadsheet-parser'
import { StepDetect } from '@/components/import-wizard/step-detect'
import { StepMetadata } from '@/components/import-wizard/step-metadata'
import { StepColumnMapping } from '@/components/import-wizard/step-column-mapping'
import { StepGermplasmReview } from '@/components/import-wizard/step-germplasm-review'
import { StepUpload } from '@/components/import-wizard/step-upload'
import { StepConfirm } from '@/components/import-wizard/step-confirm'
import { GenomicWizard } from '@/components/import-wizard/genomic/genomic-wizard'
import { cn } from '@/lib/utils'
import { Search, FileText, Upload, CheckCircle, TableProperties, Users } from 'lucide-react'

export interface ImportMetadata {
  experimentId: string | null
  experimentName: string
  sensorPlatformName: string
  sensorName: string
  datasetNames: string[]
  createNew: {
    experiment: boolean
    sensorPlatform: boolean
    sensor: boolean
  }
}

export interface TraitColumn {
  /** Original header text in the sheet — the key used to look up values in row objects. */
  columnHeader: string
  /** Editable trait label, defaults to columnHeader. Becomes the Trait entity name. */
  traitName: string
  /** Optional units string (e.g. "cm", "count", "g/m²"). Stored on the Trait entity. */
  units: string
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
  /** When true the sheet is excluded from import — no configuration required. */
  skipped: boolean
  /** Plot number column — the primary row identifier. Required for the sheet to be valid. */
  plotNumberColumn: string | null
  /** Optional plot row. May only be set if plotNumberColumn is also set. */
  plotRowColumn: string | null
  /** Optional plot column. May only be set if plotNumberColumn is also set. */
  plotColumnColumn: string | null
  /** All trait columns the user has configured (enabled or not — disabled entries preserve label edits). */
  traitColumns: TraitColumn[]
  /** Population name for this sheet. All rows belong to this population. */
  populationName: string
  /** Optional column holding canonical accession names (e.g. "SL-58-6-8-09"). */
  accessionNameColumn: string | null
  /** Optional column holding canonical line names (e.g. "MAGIC110", "B73"). */
  lineNameColumn: string | null
  /** Optional column holding arbitrary aliases / field-book shorthands
   *  (e.g. "1", "2", "Check1"). Resolved against accession_aliases. */
  aliasColumn: string | null
  /** How the collection date is determined: 'fixed' uses collectionDate, 'column' uses collectionDateColumn, 'unknown' leaves it unspecified. */
  collectionDateMode: 'fixed' | 'column' | 'unknown'
  /** Fixed collection date (YYYY-MM-DD) when mode is 'fixed'. */
  collectionDate: string
  /** Column header for per-row collection dates when mode is 'column'. */
  collectionDateColumn: string | null
  /** How the season is determined: 'fixed' uses seasonName for every row, 'column' reads per-row from seasonColumn. */
  seasonMode: 'fixed' | 'column'
  /** Fixed season name for this sheet when mode is 'fixed'. */
  seasonName: string
  /** Column header for per-row season names when mode is 'column'. */
  seasonColumn: string | null
  /** How the site is determined: 'fixed' uses siteName for every row, 'column' reads per-row from siteColumn. */
  siteMode: 'fixed' | 'column'
  /** Fixed site name for this sheet when mode is 'fixed'. */
  siteName: string
  /** Column header for per-row site names when mode is 'column'. */
  siteColumn: string | null
  /** Optional timestamp column. If unmapped, timestamps are derived from the collection date. */
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

/**
 * Output of the germplasm review step: records the user's decisions on
 * unresolved germplasm names so the upload step can proceed without
 * re-resolving.
 */
export interface GermplasmReview {
  /** Every germplasm value encountered across sheets, deduped. */
  allNames: string[]
  /** Map of input_name → resolution outcome (canonical accession/line). */
  resolved: Record<string, {
    match_kind: string
    accession_id?: string | null
    line_id?: string | null
    canonical_name?: string | null
  }>
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
  germplasmReview: GermplasmReview | null
  uploadResults: UploadResults | null
}

const BASE_STEPS = [
  { label: 'Detect', icon: Search },
  { label: 'Metadata', icon: FileText },
  { label: 'Upload', icon: Upload },
  { label: 'Confirm', icon: CheckCircle },
] as const

const MAPPING_STEP = { label: 'Map Columns', icon: TableProperties } as const
const GERMPLASM_STEP = { label: 'Review Germplasm', icon: Users } as const

/** True if any mapped sheet tagged at least one germplasm column. */
function mappingHasGermplasm(mapping: ColumnMapping | null): boolean {
  if (!mapping) return false
  return mapping.sheetConfigs.some(
    (c) => !c.skipped && (c.accessionNameColumn || c.lineNameColumn || c.aliasColumn),
  )
}

/**
 * Classify the germplasm columns across every active sheet. When every
 * sheet maps exactly one *kind* of germplasm column — only accession
 * columns, or only line columns — we know what entity to auto-create and
 * can skip the manual review step. Mixed kinds (aliases, or both
 * accession- and line-columns across sheets) remain ambiguous and require
 * per-row review.
 */
export type GermplasmMappingMode = 'none' | 'accession-only' | 'line-only' | 'ambiguous'

export function germplasmMappingMode(mapping: ColumnMapping | null): GermplasmMappingMode {
  if (!mapping) return 'none'
  let sawAccession = false
  let sawLine = false
  let sawAlias = false
  for (const c of mapping.sheetConfigs) {
    if (c.skipped) continue
    if (c.accessionNameColumn) sawAccession = true
    if (c.lineNameColumn) sawLine = true
    if (c.aliasColumn) sawAlias = true
  }
  if (!sawAccession && !sawLine && !sawAlias) return 'none'
  if (sawAlias) return 'ambiguous'
  if (sawAccession && sawLine) return 'ambiguous'
  if (sawAccession) return 'accession-only'
  return 'line-only'
}

export function WizardShell() {
  const [step, setStep] = useState(0)
  const [state, setState] = useState<WizardState>({
    files: [],
    detection: null,
    metadata: null,
    columnMapping: null,
    germplasmReview: null,
    uploadResults: null,
  })

  const needsMapping = state.detection?.dataCategories.some(c => c === 'csv_tabular') ?? false
  // Germplasm review is only shown when the mapping is ambiguous — that
  // is, when the sheets mix accession/line/alias columns and the wizard
  // can't safely guess which entity to create per row. When the mapping
  // is unambiguous ('accession-only' or 'line-only'), the upload step
  // auto-creates entities of the right kind without prompting.
  const needsGermplasm =
    needsMapping && germplasmMappingMode(state.columnMapping) === 'ambiguous'

  const steps = useMemo(() => {
    const s: { label: string; icon: typeof Search }[] = [BASE_STEPS[0], BASE_STEPS[1]]
    if (needsMapping) s.push(MAPPING_STEP)
    if (needsGermplasm) s.push(GERMPLASM_STEP)
    s.push(BASE_STEPS[2], BASE_STEPS[3])
    return s
  }, [needsMapping, needsGermplasm])

  // Step indices. Base layout: 0 Detect, 1 Metadata, then optional Mapping,
  // optional Germplasm, then Upload, Confirm.
  const mappingStepIndex = 2 // only valid when needsMapping is true
  const germplasmStepIndex = needsMapping ? 3 : -1 // only valid when needsGermplasm is true
  const uploadStepIndex =
    (needsMapping ? 1 : 0) + (needsGermplasm ? 1 : 0) + 2
  const confirmStepIndex = uploadStepIndex + 1

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
    setState((prev) => ({ ...prev, columnMapping: mapping, germplasmReview: null }))
    // Only route through the review step when mapping is genuinely
    // ambiguous. Unambiguous (or no) germplasm mapping → upload creates
    // the right entity kind inline.
    if (germplasmMappingMode(mapping) === 'ambiguous') {
      setStep(3) // germplasm review
    } else {
      setStep(3) // upload (index 3 when no germplasm step is present)
    }
  }, [])

  const handleGermplasmNext = useCallback((review: GermplasmReview) => {
    setState((prev) => ({ ...prev, germplasmReview: review }))
    setStep(4) // upload (index 4 when germplasm step is present)
  }, [])

  const handleUploadNext = useCallback((results: UploadResults) => {
    setState((prev) => ({ ...prev, uploadResults: results }))
    setStep(confirmStepIndex)
  }, [confirmStepIndex])

  const handleDone = useCallback(() => {
    setState({
      files: [],
      detection: null,
      metadata: null,
      columnMapping: null,
      germplasmReview: null,
      uploadResults: null,
    })
    setStep(0)
  }, [])

  const handleBack = useCallback((toStep: number) => {
    setStep(toStep)
  }, [])

  const handleGenomicExit = useCallback(() => {
    setState({
      files: [],
      detection: null,
      metadata: null,
      columnMapping: null,
      germplasmReview: null,
      uploadResults: null,
    })
    setStep(0)
  }, [])

  // Route genomic imports (HapMap, VCF, HapMap-style matrix xlsx) to a
  // dedicated wizard. Detection populates genomicShape when the file's
  // structure is recognized as genomic. The early return MUST come after
  // every hook call above — otherwise re-renders produce a different hook
  // count and React throws "Rendered fewer hooks than expected".
  const isGenomic =
    state.detection !== null &&
    state.detection.dataCategories.includes('genomic') &&
    state.detection.genomicShape != null &&
    state.detection.genomicFile != null

  if (isGenomic && state.detection) {
    return (
      <GenomicWizard
        files={state.files}
        detection={state.detection}
        onExit={handleGenomicExit}
      />
    )
  }

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
          initial={state.metadata}
          onNext={handleMetadataNext}
          onBack={() => handleBack(0)}
        />
      )}

      {needsMapping && step === mappingStepIndex && state.detection && state.metadata && (
        <StepColumnMapping
          files={state.files}
          initial={state.columnMapping}
          onNext={handleMappingNext}
          onBack={() => handleBack(1)}
        />
      )}

      {needsGermplasm && step === germplasmStepIndex && state.columnMapping && state.metadata && (
        <StepGermplasmReview
          mapping={state.columnMapping}
          metadata={state.metadata}
          initial={state.germplasmReview}
          onNext={handleGermplasmNext}
          onBack={() => handleBack(mappingStepIndex)}
        />
      )}

      {step === uploadStepIndex && state.detection && state.metadata && (
        <StepUpload
          files={state.files}
          detection={state.detection}
          metadata={state.metadata}
          columnMapping={state.columnMapping}
          germplasmReview={state.germplasmReview}
          onNext={handleUploadNext}
          onBack={() =>
            handleBack(
              needsGermplasm ? germplasmStepIndex :
              needsMapping ? mappingStepIndex : 1,
            )
          }
        />
      )}

      {step === confirmStepIndex && state.uploadResults && (
        <StepConfirm results={state.uploadResults} onDone={handleDone} />
      )}
    </div>
  )
}
