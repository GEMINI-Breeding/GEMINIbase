import { useState, useEffect, useRef } from 'react'
import type { FileWithPath } from '@/components/upload/dropzone'
import type { DetectionResult } from '@/components/import-wizard/detection-engine'
import type {
  ImportMetadata,
  UploadResults,
  ColumnMapping,
  GermplasmReview,
  SheetMapping,
} from '@/components/import-wizard/wizard-shell'
import { germplasmMappingMode } from '@/components/import-wizard/wizard-shell'
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
import { populationsApi } from '@/api/endpoints/populations'
import { plotsApi } from '@/api/endpoints/plots'
import { accessionsApi } from '@/api/endpoints/accessions'
import { linesApi } from '@/api/endpoints/lines'
import { Loader2, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'

interface StepUploadProps {
  files: FileWithPath[]
  detection: DetectionResult
  metadata: ImportMetadata
  columnMapping?: ColumnMapping | null
  /** Output of the germplasm review step (null when no germplasm columns
   *  were mapped — in that case plots are created without accession links,
   *  matching the pre-resolver behavior). */
  germplasmReview?: GermplasmReview | null
  onNext: (results: UploadResults) => void
  onBack: () => void
}

/**
 * For a row, return the germplasm cell value + which column role it came
 * from. Preference order matches the resolver's precedence: accession >
 * line > alias. This lets us use the most specific column the user tagged.
 */
function pickGermplasmFromRow(
  row: Record<string, unknown>,
  config: SheetMapping,
): string | null {
  const tryColumn = (col: string | null): string | null => {
    if (!col) return null
    const v = row[col]
    if (v == null) return null
    const trimmed = String(v).trim()
    return trimmed || null
  }
  return (
    tryColumn(config.accessionNameColumn) ??
    tryColumn(config.lineNameColumn) ??
    tryColumn(config.aliasColumn)
  )
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

/**
 * Visible progress for the setup phase that runs between file upload and
 * record ingestion. Populating this lets the user see that the wizard is
 * still working (creating traits, populations, plots, etc.) rather than
 * staring at a static "File Upload: Complete" card.
 */
interface SetupProgress {
  traits: { done: number; total: number }
  populations: { done: number; total: number }
  seasons: { done: number; total: number }
  sites: { done: number; total: number }
  germplasm: { done: number; total: number }
  plots: { done: number; total: number }
}

const EMPTY_SETUP: SetupProgress = {
  traits: { done: 0, total: 0 },
  populations: { done: 0, total: 0 },
  seasons: { done: 0, total: 0 },
  sites: { done: 0, total: 0 },
  germplasm: { done: 0, total: 0 },
  plots: { done: 0, total: 0 },
}

export function StepUpload({ files, detection, metadata, columnMapping, germplasmReview, onNext, onBack }: StepUploadProps) {
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
  const [setupProgress, setSetupProgress] = useState<SetupProgress>(EMPTY_SETUP)
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

        // -------------------------------------------------------------
        // Setup phase: create the entities that the record insert needs
        // (traits, populations, seasons, sites, plots). We count up the
        // work first, then execute with visible progress so the user
        // isn't staring at a static "Upload complete" card while the
        // wizard churns through hundreds of sequential creates.
        // -------------------------------------------------------------

        const traitUnits = new Map<string, string>()
        for (const config of sheetConfigs) {
          if (!config || config.skipped) continue
          for (const tc of config.traitColumns.filter((t) => t.enabled)) {
            if (!traitUnits.has(tc.traitName)) traitUnits.set(tc.traitName, tc.units || '')
          }
        }

        const populationNames = new Set<string>()
        for (const config of sheetConfigs) {
          if (!config || config.skipped) continue
          if (config.populationName.trim()) populationNames.add(config.populationName.trim())
        }

        const seasonNamesToCreate = new Set<string>()
        const siteNamesToCreate = new Set<string>()
        for (let si = 0; si < sheets.length; si++) {
          const config = sheetConfigs[si]
          if (!config || config.skipped) continue
          if (config.seasonMode === 'fixed' && config.seasonName.trim()) {
            seasonNamesToCreate.add(config.seasonName.trim())
          } else if (config.seasonMode === 'column' && config.seasonColumn) {
            for (const row of sheets[si].rows) {
              const v = row[config.seasonColumn]
              if (v != null && String(v).trim() !== '') seasonNamesToCreate.add(String(v).trim())
            }
          }
          if (config.siteMode === 'fixed' && config.siteName.trim()) {
            siteNamesToCreate.add(config.siteName.trim())
          } else if (config.siteMode === 'column' && config.siteColumn) {
            for (const row of sheets[si].rows) {
              const v = row[config.siteColumn]
              if (v != null && String(v).trim() !== '') siteNamesToCreate.add(String(v).trim())
            }
          }
        }

        // Collect unique plot specs up front so we can show a total.
        // Matching defaults (row/col = 0 when unmapped) used again below
        // when building trait records.
        type PlotSpec = {
          plotNumber: number
          plotRow: number
          plotCol: number
          season: string
          site: string
          population?: string
          /** Canonical accession name resolved from the spreadsheet's
           *  germplasm cell via the review step, or — when the mapping is
           *  unambiguous — derived inline from the row value. Undefined
           *  when no germplasm column was mapped or the row was marked
           *  'skip'. */
          accessionName?: string
        }
        // Determine the germplasm-creation mode. When the mapping is
        // unambiguous ('accession-only' or 'line-only') the wizard skips
        // the review step and auto-creates entities inline here. Only
        // 'ambiguous' reaches the review step and provides a
        // `germplasmReview` object.
        const gplasmMode = germplasmMappingMode(columnMapping)
        const plotSpecs: PlotSpec[] = []
        const plotKeySeen = new Set<string>()
        const resolutionMap = germplasmReview?.resolved ?? {}
        const missingGermplasmRefs = new Set<string>()
        // Set of unique raw germplasm values encountered across every
        // sheet — used when gplasmMode is accession-only / line-only so
        // we can pre-create entities before plot creation.
        const inlineGermplasmNames = new Set<string>()
        for (let si = 0; si < sheets.length; si++) {
          const sheet = sheets[si]
          const config = sheetConfigs[si]
          if (!config || config.skipped || !config.plotNumberColumn) continue
          const populationName = config.populationName.trim() || undefined
          for (const row of sheet.rows) {
            const plotRaw = row[config.plotNumberColumn]
            if (plotRaw == null || plotRaw === '') continue
            const plotNumber = Number(plotRaw)
            if (Number.isNaN(plotNumber)) continue

            let plotRow = 0
            if (config.plotRowColumn && row[config.plotRowColumn] != null) {
              const v = Number(row[config.plotRowColumn])
              if (!Number.isNaN(v)) plotRow = v
            }
            let plotCol = 0
            if (config.plotColumnColumn && row[config.plotColumnColumn] != null) {
              const v = Number(row[config.plotColumnColumn])
              if (!Number.isNaN(v)) plotCol = v
            }

            const rowSeason = config.seasonMode === 'column' && config.seasonColumn
              ? (row[config.seasonColumn] != null ? String(row[config.seasonColumn]).trim() : '')
              : config.seasonName.trim()
            const rowSite = config.siteMode === 'column' && config.siteColumn
              ? (row[config.siteColumn] != null ? String(row[config.siteColumn]).trim() : '')
              : config.siteName.trim()
            if (!rowSeason || !rowSite) continue

            // Resolve germplasm for this row. Two branches:
            //   - ambiguous mapping → trust the review step's `resolved`
            //     map, keyed on the raw input name. Unresolved rows get
            //     no accession link.
            //   - unambiguous (accession-only or line-only) → use the
            //     raw value as the canonical accession name. For
            //     line-only we still land on accession_name because
            //     plot only has an accession_id FK; the inline create
            //     step below materializes a Line AND an Accession (with
            //     line_id linking them) so a later genomic import
            //     resolves against either.
            let accessionName: string | undefined
            const rowGermplasm = pickGermplasmFromRow(row, config)
            if (rowGermplasm) {
              if (gplasmMode === 'ambiguous') {
                const hit = resolutionMap[rowGermplasm]
                if (hit && hit.canonical_name && hit.match_kind !== 'unresolved') {
                  accessionName = hit.canonical_name
                } else if (!hit) {
                  missingGermplasmRefs.add(rowGermplasm)
                }
              } else {
                accessionName = rowGermplasm
                inlineGermplasmNames.add(rowGermplasm)
              }
            }

            const key = `${rowSeason}::${rowSite}::${plotNumber}::${plotRow}::${plotCol}`
            if (plotKeySeen.has(key)) continue
            plotKeySeen.add(key)
            plotSpecs.push({
              plotNumber,
              plotRow,
              plotCol,
              season: rowSeason,
              site: rowSite,
              population: populationName,
              accessionName,
            })
          }
        }

        // Seed totals so the UI immediately shows the scope of the work.
        setSetupProgress({
          traits: { done: 0, total: traitUnits.size },
          populations: { done: 0, total: populationNames.size },
          seasons: { done: 0, total: seasonNamesToCreate.size },
          sites: { done: 0, total: siteNamesToCreate.size },
          germplasm: { done: 0, total: inlineGermplasmNames.size },
          plots: { done: 0, total: plotSpecs.length },
        })

        const tick = (key: keyof SetupProgress) =>
          setSetupProgress((prev) => ({
            ...prev,
            [key]: { done: prev[key].done + 1, total: prev[key].total },
          }))

        // Resolve/create trait entities. `Trait.create` uses get_or_create
        // at the DB layer, so we skip the pre-search that was otherwise
        // producing a noisy trail of 404s in the browser console.
        const traitIdCache = new Map<string, string>()
        for (const [name, units] of traitUnits) {
          if (abortedRef.current) return
          const created = await traitsApi.create({
            trait_name: name,
            trait_units: units.trim() || undefined,
            trait_level_id: 0 as unknown as string,
            experiment_name: metadata.experimentName,
          })
          if (!created.id) throw new Error(`Failed to resolve trait ID for "${name}"`)
          traitIdCache.set(name, created.id)
          tick('traits')
        }

        for (const name of populationNames) {
          if (abortedRef.current) return
          try {
            await populationsApi.create({
              population_name: name,
              experiment_name: metadata.experimentName,
            })
          } catch {
            // population may already exist — safe to ignore
          }
          tick('populations')
        }

        for (const name of seasonNamesToCreate) {
          if (abortedRef.current) return
          try {
            await seasonsApi.create({ season_name: name, experiment_name: metadata.experimentName })
          } catch {
            // already exists — safe to ignore
          }
          tick('seasons')
        }
        for (const name of siteNamesToCreate) {
          if (abortedRef.current) return
          try {
            await sitesApi.create({ site_name: name, experiment_name: metadata.experimentName })
          } catch {
            // already exists — safe to ignore
          }
          tick('sites')
        }

        // Unambiguous-mapping branch: pre-create Accession (and Line, if
        // the user mapped a line column) entities for every unique raw
        // value in the germplasm column. For line-only mapping we create
        // the Line first, then an Accession with the same name linked to
        // that Line — so plots reference a real accession and a later
        // genomic import can resolve the sample headers via either
        // 'accession_exact' or 'line_exact'. Creates are idempotent
        // thanks to get_or_create in the backend.
        //
        // Each accession is also linked to a population (the first one
        // we see for it in plotSpecs). Without this link the experiment
        // cascade-delete can't reach these accessions — they'd end up as
        // DB orphans once the experiment and its plots are gone (same
        // bug the genomic wizard had).
        const populationForAccession = new Map<string, string>()
        for (const spec of plotSpecs) {
          if (!spec.accessionName || !spec.population) continue
          if (!populationForAccession.has(spec.accessionName)) {
            populationForAccession.set(spec.accessionName, spec.population)
          }
        }
        if (gplasmMode === 'line-only') {
          for (const name of inlineGermplasmNames) {
            if (abortedRef.current) return
            try {
              await linesApi.create({ line_name: name })
            } catch {
              // already exists — safe to ignore
            }
            try {
              const popName = populationForAccession.get(name)
              await accessionsApi.create({
                accession_name: name,
                line_name: name,
                ...(popName ? { population_name: popName } : {}),
              })
            } catch {
              // already exists — safe to ignore
            }
            tick('germplasm')
          }
        } else if (gplasmMode === 'accession-only') {
          for (const name of inlineGermplasmNames) {
            if (abortedRef.current) return
            try {
              const popName = populationForAccession.get(name)
              await accessionsApi.create({
                accession_name: name,
                ...(popName ? { population_name: popName } : {}),
              })
            } catch {
              // already exists — safe to ignore
            }
            tick('germplasm')
          }
        }

        // Pre-create plot rows via the bulk endpoint. The single-plot
        // POST route resolves five name-keyed FKs per request
        // (experiment/season/site/accession/population), so a
        // thousand-row spreadsheet fired thousands of HTTP round trips
        // and tens of thousands of DB queries. The bulk route batches
        // the FK lookups and issues a single INSERT ... ON CONFLICT DO
        // NOTHING. We chunk at 500 so the request body stays modest and
        // progress can tick in visible increments.
        const PLOT_CHUNK = 500
        for (let i = 0; i < plotSpecs.length; i += PLOT_CHUNK) {
          if (abortedRef.current) return
          const chunk = plotSpecs.slice(i, i + PLOT_CHUNK)
          await plotsApi.createBulk(
            chunk.map((spec) => ({
              plot_number: spec.plotNumber,
              plot_row_number: spec.plotRow,
              plot_column_number: spec.plotCol,
              experiment_name: metadata.experimentName,
              season_name: spec.season,
              site_name: spec.site,
              population_name: spec.population,
              accession_name: spec.accessionName,
            })),
          )
          for (let j = 0; j < chunk.length; j++) tick('plots')
        }

        // Pre-compute per-(sheet, trait) totals so the progress UI can show
        // running totals without waiting until the end. A cell counts only if
        // both the trait value AND plot_number are present and numeric.
        const perTraitTotal = new Map<string, number>()
        let grandTotal = 0
        for (let si = 0; si < sheets.length; si++) {
          const sheet = sheets[si]
          const config = sheetConfigs[si]
          if (!config || config.skipped || !config.plotNumberColumn) continue
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
        let tsOffset = 0
        let runningCurrent = 0
        const perTraitCurrent = new Map<string, number>()

        for (let si = 0; si < sheets.length; si++) {
          if (abortedRef.current) return
          const sheet = sheets[si]
          const config = sheetConfigs[si]
          // Plot number is the required row identifier — skip sheets that
          // somehow got here without one (wizard validation should prevent it).
          if (!config || config.skipped || !config.plotNumberColumn) continue

          // Resolve base date for auto-generated timestamps on this sheet.
          const sheetBaseDate = config.collectionDateMode === 'fixed' && config.collectionDate
            ? new Date(config.collectionDate + 'T12:00:00')
            : new Date()

          // Fixed collection date string for the bulk API call.
          const sheetCollectionDate = config.collectionDateMode === 'fixed' && config.collectionDate
            ? config.collectionDate
            : undefined

          const enabledTraits = config.traitColumns.filter((tc) => tc.enabled)
          for (const trait of enabledTraits) {
            if (abortedRef.current) return
            const traitKey = `${sheet.name}::${trait.traitName}`
            setIngestionProgress((prev) => ({
              ...prev,
              currentSheet: sheet.name,
              currentTrait: trait.traitName,
            }))

            const traitId = traitIdCache.get(trait.traitName)
            if (!traitId) throw new Error(`Trait "${trait.traitName}" was not resolved during setup`)

            // Build all valid records for this (sheet, trait) pair, grouped by (season, site).
            const recordGroups = new Map<string, Record<string, unknown>[]>()
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

              // Default row/col to 0 when the user didn't map those columns
              // so the trigger's exact-match lookup finds the plot we
              // pre-created above.
              let plotRow = 0
              if (config.plotRowColumn && row[config.plotRowColumn] != null) {
                const v = Number(row[config.plotRowColumn])
                if (!Number.isNaN(v)) plotRow = v
              }
              let plotCol = 0
              if (config.plotColumnColumn && row[config.plotColumnColumn] != null) {
                const v = Number(row[config.plotColumnColumn])
                if (!Number.isNaN(v)) plotCol = v
              }

              const record: Record<string, unknown> = {
                trait_value: value,
                plot_number: plotNumber,
                plot_row_number: plotRow,
                plot_column_number: plotCol,
              }

              // Build record_info: sheet name, source column, the raw
              // germplasm cells (whitespace-trimmed; the canonical accession
              // lookup happens via plot.accession_id), and any user-selected
              // metadata columns.
              const recordInfo: Record<string, unknown> = {
                sheet: sheet.name,
                source_column: trait.columnHeader,
              }
              if (config.populationName.trim()) {
                recordInfo.population = config.populationName.trim()
              }
              if (config.accessionNameColumn) {
                const v = row[config.accessionNameColumn]
                recordInfo.accession_name = v != null ? String(v).trim() : null
              }
              if (config.lineNameColumn) {
                const v = row[config.lineNameColumn]
                recordInfo.line_name = v != null ? String(v).trim() : null
              }
              if (config.aliasColumn) {
                const v = row[config.aliasColumn]
                recordInfo.germplasm_alias = v != null ? String(v).trim() : null
              }
              for (const mc of config.metadataColumns) {
                const v = row[mc.columnHeader]
                recordInfo[mc.label] = v != null ? v : null
              }
              record.record_info = recordInfo

              // Timestamp: explicit column > collection-date column > fixed collection date > now
              if (config.timestampColumn && row[config.timestampColumn] != null) {
                record.timestamp = String(row[config.timestampColumn])
              } else if (config.collectionDateMode === 'column' && config.collectionDateColumn) {
                const cdRaw = row[config.collectionDateColumn]
                if (cdRaw != null && String(cdRaw).trim() !== '') {
                  record.timestamp = new Date(String(cdRaw) + 'T12:00:00').toISOString()
                } else {
                  record.timestamp = new Date(sheetBaseDate.getTime() + tsOffset * 1000).toISOString()
                }
              } else {
                record.timestamp = new Date(sheetBaseDate.getTime() + tsOffset * 1000).toISOString()
              }
              tsOffset++

              const rowSeason = config.seasonMode === 'column' && config.seasonColumn
                ? (row[config.seasonColumn] != null ? String(row[config.seasonColumn]).trim() : '')
                : config.seasonName.trim()
              const rowSite = config.siteMode === 'column' && config.siteColumn
                ? (row[config.siteColumn] != null ? String(row[config.siteColumn]).trim() : '')
                : config.siteName.trim()
              const key = `${rowSeason}::${rowSite}`
              if (!recordGroups.has(key)) recordGroups.set(key, [])
              recordGroups.get(key)!.push(record)
            }

            // POST in batches, per (season, site) group
            for (const [groupKey, groupRecords] of recordGroups) {
              if (abortedRef.current) return
              const [groupSeason, groupSite] = groupKey.split('::')
              for (let offset = 0; offset < groupRecords.length; offset += BATCH_SIZE) {
                if (abortedRef.current) return
                const batch = groupRecords.slice(offset, offset + BATCH_SIZE)
                await traitsApi.bulkCreateRecords(traitId, {
                  records: batch,
                  experiment_name: metadata.experimentName,
                  season_name: groupSeason,
                  site_name: groupSite,
                  dataset_name: metadata.datasetNames[0] || undefined,
                  collection_date: sheetCollectionDate,
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

      {/* Setup progress — shown while we resolve traits and pre-create
          populations/seasons/sites/plots before record ingestion begins.
          Without this, the wizard appeared to hang after file upload for
          as long as plot creation took on large spreadsheets. */}
      {(phase === 'ingesting' || (phase === 'done' && columnMapping)) &&
        (setupProgress.traits.total +
          setupProgress.populations.total +
          setupProgress.seasons.total +
          setupProgress.sites.total +
          setupProgress.germplasm.total +
          setupProgress.plots.total) > 0 && (
        <div className="rounded-lg border p-4 space-y-3" data-testid="setup-progress">
          <h3 className="font-medium">Preparing Records</h3>
          <div className="space-y-1.5 text-sm">
            {([
              ['Traits', setupProgress.traits],
              ['Populations', setupProgress.populations],
              ['Seasons', setupProgress.seasons],
              ['Sites', setupProgress.sites],
              ['Germplasm', setupProgress.germplasm],
              ['Plots', setupProgress.plots],
            ] as const)
              .filter(([, p]) => p.total > 0)
              .map(([label, p]) => {
                const finished = p.done >= p.total
                return (
                  <div key={label} className="flex items-center gap-2">
                    {finished ? (
                      <CheckCircle className="w-4 h-4 text-green-600 shrink-0" />
                    ) : (
                      <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />
                    )}
                    <span className="font-medium">{label}</span>
                    <span className="ml-auto tabular-nums text-muted-foreground">
                      {p.done} / {p.total}
                    </span>
                  </div>
                )
              })}
          </div>
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
