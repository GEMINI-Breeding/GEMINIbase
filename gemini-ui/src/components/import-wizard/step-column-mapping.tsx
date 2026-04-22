import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { FileWithPath } from '@/components/upload/dropzone'
import type {
  ColumnMapping,
  SheetMapping,
  TraitColumn,
  MetadataColumn,
} from '@/components/import-wizard/wizard-shell'
import { parseSpreadsheet, type ParsedSheet } from '@/lib/spreadsheet-parser'
import { populationsApi } from '@/api/endpoints/populations'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import { Loader2, ChevronLeft, ChevronRight, X, Plus } from 'lucide-react'

interface StepColumnMappingProps {
  files: FileWithPath[]
  /** When the user navigates back to this step, restore their prior mapping
   *  instead of re-parsing the file and discarding every selection. */
  initial: ColumnMapping | null
  onNext: (mapping: ColumnMapping) => void
  onBack: () => void
}

const NOT_MAPPED = '__not_mapped__'

function emptySheetConfig(sheet: ParsedSheet): SheetMapping {
  return {
    sheetName: sheet.name,
    skipped: false,
    plotNumberColumn: null,
    plotRowColumn: null,
    plotColumnColumn: null,
    populationName: '',
    traitColumns: [],
    accessionNameColumn: null,
    lineNameColumn: null,
    aliasColumn: null,
    collectionDateMode: 'fixed',
    collectionDate: '',
    collectionDateColumn: null,
    seasonMode: 'fixed',
    seasonName: '',
    seasonColumn: null,
    siteMode: 'fixed',
    siteName: '',
    siteColumn: null,
    timestampColumn: null,
    metadataColumns: [],
  }
}

/**
 * Seed a new sheet's config from the most recently visited sheet, carrying
 * forward mappings by matching column headers. Mappings for columns that don't
 * exist in the new sheet are dropped. Trait and metadata label edits are
 * preserved for columns that do exist.
 */
function seedSheetConfig(
  prev: SheetMapping | null,
  sheet: ParsedSheet,
): SheetMapping {
  if (!prev) return emptySheetConfig(sheet)
  const headerSet = new Set(sheet.headers)
  const copyIfPresent = (col: string | null) =>
    col && headerSet.has(col) ? col : null
  return {
    sheetName: sheet.name,
    skipped: false,
    plotNumberColumn: copyIfPresent(prev.plotNumberColumn),
    plotRowColumn: copyIfPresent(prev.plotRowColumn),
    plotColumnColumn: copyIfPresent(prev.plotColumnColumn),
    populationName: prev.populationName,
    traitColumns: prev.traitColumns
      .filter((tc) => headerSet.has(tc.columnHeader))
      .map((tc) => ({ ...tc })),
    accessionNameColumn: copyIfPresent(prev.accessionNameColumn),
    lineNameColumn: copyIfPresent(prev.lineNameColumn),
    aliasColumn: copyIfPresent(prev.aliasColumn),
    collectionDateMode: prev.collectionDateMode,
    collectionDate: prev.collectionDate,
    collectionDateColumn: copyIfPresent(prev.collectionDateColumn),
    seasonMode: prev.seasonMode,
    seasonName: prev.seasonName,
    seasonColumn: copyIfPresent(prev.seasonColumn),
    siteMode: prev.siteMode,
    siteName: prev.siteName,
    siteColumn: copyIfPresent(prev.siteColumn),
    timestampColumn: copyIfPresent(prev.timestampColumn),
    metadataColumns: prev.metadataColumns
      .filter((mc) => headerSet.has(mc.columnHeader))
      .map((mc) => ({ ...mc })),
  }
}

/** True if the sheet config looks untouched — matches defaults produced by
 * emptySheetConfig. If so it's safe to re-seed from the previous sheet. */
function isPristine(config: SheetMapping): boolean {
  return (
    !config.skipped &&
    config.plotNumberColumn === null &&
    config.plotRowColumn === null &&
    config.plotColumnColumn === null &&
    config.populationName === '' &&
    config.traitColumns.length === 0 &&
    config.accessionNameColumn === null &&
    config.lineNameColumn === null &&
    config.aliasColumn === null &&
    config.collectionDateMode === 'fixed' &&
    config.collectionDate === '' &&
    config.collectionDateColumn === null &&
    config.seasonMode === 'fixed' &&
    config.seasonName === '' &&
    config.seasonColumn === null &&
    config.siteMode === 'fixed' &&
    config.siteName === '' &&
    config.siteColumn === null &&
    config.timestampColumn === null &&
    config.metadataColumns.length === 0
  )
}

const CREATE_NEW = '__create_new__'
const NOT_SPECIFIED = ''

function PopulationField({
  value,
  onChange,
  existing,
}: {
  value: string
  onChange: (v: string) => void
  existing: string[]
}) {
  // Derived mode from the current value: if blank, not specified; if it
  // matches an existing population, that one is selected; otherwise the
  // user is in "create new" mode.
  const derivedMode: 'none' | 'existing' | 'new' =
    value.trim() === ''
      ? 'none'
      : existing.includes(value.trim())
        ? 'existing'
        : 'new'
  // Local override lets the user enter "create new" mode even before they
  // type anything (blank populationName).
  const [localMode, setLocalMode] = useState<'none' | 'existing' | 'new' | null>(null)
  const mode = localMode ?? derivedMode

  const selectValue =
    mode === 'none' ? NOT_SPECIFIED
    : mode === 'new' ? CREATE_NEW
    : value

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <h3 className="font-medium">Population name (optional)</h3>
      <p className="text-sm text-muted-foreground">
        The germplasm population that all rows in this sheet belong to (e.g.
        a diversity panel or RIL population). Pick an existing population or
        create a new one. Leave unspecified if it doesn't apply.
      </p>
      <Select
        value={selectValue}
        onChange={(e) => {
          const v = e.target.value
          if (v === NOT_SPECIFIED) {
            setLocalMode('none')
            onChange('')
          } else if (v === CREATE_NEW) {
            setLocalMode('new')
            onChange('')
          } else {
            setLocalMode('existing')
            onChange(v)
          }
        }}
        data-testid="population-select"
      >
        <option value={NOT_SPECIFIED}>-- Not specified --</option>
        <option value={CREATE_NEW}>+ Create new...</option>
        {existing.map((name) => (
          <option key={name} value={name}>{name}</option>
        ))}
      </Select>
      {mode === 'new' && (
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="e.g. UC Davis Diversity Panel"
          data-testid="population-name"
          autoFocus
        />
      )}
    </div>
  )
}

function isSheetConfigValid(config: SheetMapping): boolean {
  if (config.skipped) return true
  if (!config.plotNumberColumn) return false
  const enabledTraits = config.traitColumns.filter((tc) => tc.enabled)
  if (enabledTraits.length === 0) return false
  if (!enabledTraits.every((tc) => tc.traitName.trim() !== '')) return false
  if (!config.metadataColumns.every((mc) => mc.label.trim() !== '')) return false
  if (config.seasonMode === 'fixed' && !config.seasonName.trim()) return false
  if (config.seasonMode === 'column' && !config.seasonColumn) return false
  if (config.siteMode === 'fixed' && !config.siteName.trim()) return false
  if (config.siteMode === 'column' && !config.siteColumn) return false
  if (config.collectionDateMode === 'fixed' && !config.collectionDate) return false
  if (config.collectionDateMode === 'column' && !config.collectionDateColumn) return false
  return true
}

export function StepColumnMapping({
  files,
  initial,
  onNext,
  onBack,
}: StepColumnMappingProps) {
  // Seed from `initial` so a round-trip through later steps (and the Back
  // button after a failed upload) doesn't discard the user's work.
  const [sheets, setSheets] = useState<ParsedSheet[]>(() => initial?.sheets ?? [])
  const [loading, setLoading] = useState(() => !initial)
  const [parseError, setParseError] = useState<string | null>(null)
  const [sheetIdx, setSheetIdx] = useState(0)
  const [configs, setConfigs] = useState<SheetMapping[]>(() => initial?.sheetConfigs ?? [])
  const [pendingMetadataSelect, setPendingMetadataSelect] = useState<string>(NOT_MAPPED)

  // Existing populations from the backend — lets the user pick one instead
  // of re-typing a name that already exists.
  const { data: existingPopulations } = useQuery({
    queryKey: ['populations', 'all'],
    queryFn: () => populationsApi.getAll(500, 0),
  })

  // Parse spreadsheet files on mount. Skip when we're restoring from a
  // prior visit (sheets already populated).
  useEffect(() => {
    if (initial) return
    async function parse() {
      setLoading(true)
      setParseError(null)
      try {
        const tabularFile = files.find((f) => {
          const ext = f.name.split('.').pop()?.toLowerCase() || ''
          return ['csv', 'tsv', 'txt', 'xlsx', 'xls', 'ods'].includes(ext)
        })
        if (!tabularFile) {
          setParseError('No tabular file found in uploaded files.')
          setLoading(false)
          return
        }
        const parsed = await parseSpreadsheet(tabularFile)
        if (parsed.length === 0) {
          setParseError('The file contains no data.')
          setLoading(false)
          return
        }
        setSheets(parsed)
        setSheetIdx(0)
        setConfigs(parsed.map((s) => emptySheetConfig(s)))
      } catch (err) {
        setParseError(
          err instanceof Error ? err.message : 'Failed to parse file.',
        )
      } finally {
        setLoading(false)
      }
    }
    parse()
  }, [files, initial])

  const currentSheet = sheets[sheetIdx] || null
  const currentConfig: SheetMapping | null = configs[sheetIdx] || null
  const headers = useMemo(() => currentSheet?.headers || [], [currentSheet])

  /**
   * Columns already used in a non-trait role (plot, genotype, timestamp,
   * metadata). Hidden from the trait-column selection list so a column can
   * only be used in one role at a time.
   */
  const reservedColumns = useMemo(() => {
    if (!currentConfig) return new Set<string>()
    const s = new Set<string>()
    if (currentConfig.plotNumberColumn) s.add(currentConfig.plotNumberColumn)
    if (currentConfig.plotRowColumn) s.add(currentConfig.plotRowColumn)
    if (currentConfig.plotColumnColumn) s.add(currentConfig.plotColumnColumn)
    if (currentConfig.accessionNameColumn) s.add(currentConfig.accessionNameColumn)
    if (currentConfig.lineNameColumn) s.add(currentConfig.lineNameColumn)
    if (currentConfig.aliasColumn) s.add(currentConfig.aliasColumn)
    if (currentConfig.collectionDateColumn) s.add(currentConfig.collectionDateColumn)
    if (currentConfig.seasonColumn) s.add(currentConfig.seasonColumn)
    if (currentConfig.siteColumn) s.add(currentConfig.siteColumn)
    if (currentConfig.timestampColumn) s.add(currentConfig.timestampColumn)
    for (const mc of currentConfig.metadataColumns) s.add(mc.columnHeader)
    return s
  }, [currentConfig])

  /**
   * Columns not yet used in any role. These are the candidates for
   * "Add metadata column".
   */
  const availableForMetadata = useMemo(() => {
    if (!currentConfig) return [] as string[]
    const enabledTraitHeaders = new Set(
      currentConfig.traitColumns.filter((tc) => tc.enabled).map((tc) => tc.columnHeader),
    )
    return headers.filter(
      (h) => !reservedColumns.has(h) && !enabledTraitHeaders.has(h),
    )
  }, [currentConfig, headers, reservedColumns])

  function updateCurrentConfig(updates: Partial<SheetMapping>) {
    setConfigs((prev) => {
      const next = [...prev]
      if (!next[sheetIdx]) return prev
      next[sheetIdx] = { ...next[sheetIdx], ...updates }
      return next
    })
  }

  function toggleTraitColumn(header: string, enabled: boolean) {
    setConfigs((prev) => {
      const next = [...prev]
      const config = next[sheetIdx]
      if (!config) return prev
      const existing = config.traitColumns.find((tc) => tc.columnHeader === header)
      let traitColumns: TraitColumn[]
      if (existing) {
        traitColumns = config.traitColumns.map((tc) =>
          tc.columnHeader === header ? { ...tc, enabled } : tc,
        )
      } else {
        traitColumns = [
          ...config.traitColumns,
          { columnHeader: header, traitName: header, units: '', enabled },
        ]
      }
      next[sheetIdx] = { ...config, traitColumns }
      return next
    })
  }

  function updateTraitLabel(header: string, label: string) {
    setConfigs((prev) => {
      const next = [...prev]
      const config = next[sheetIdx]
      if (!config) return prev
      next[sheetIdx] = {
        ...config,
        traitColumns: config.traitColumns.map((tc) =>
          tc.columnHeader === header ? { ...tc, traitName: label } : tc,
        ),
      }
      return next
    })
  }

  function updateTraitUnits(header: string, units: string) {
    setConfigs((prev) => {
      const next = [...prev]
      const config = next[sheetIdx]
      if (!config) return prev
      next[sheetIdx] = {
        ...config,
        traitColumns: config.traitColumns.map((tc) =>
          tc.columnHeader === header ? { ...tc, units } : tc,
        ),
      }
      return next
    })
  }

  function addMetadataColumn(header: string) {
    if (header === NOT_MAPPED) return
    setConfigs((prev) => {
      const next = [...prev]
      const config = next[sheetIdx]
      if (!config) return prev
      if (config.metadataColumns.some((mc) => mc.columnHeader === header)) return prev
      const entry: MetadataColumn = { columnHeader: header, label: header }
      next[sheetIdx] = {
        ...config,
        metadataColumns: [...config.metadataColumns, entry],
      }
      return next
    })
    setPendingMetadataSelect(NOT_MAPPED)
  }

  function removeMetadataColumn(header: string) {
    setConfigs((prev) => {
      const next = [...prev]
      const config = next[sheetIdx]
      if (!config) return prev
      next[sheetIdx] = {
        ...config,
        metadataColumns: config.metadataColumns.filter((mc) => mc.columnHeader !== header),
      }
      return next
    })
  }

  function updateMetadataLabel(header: string, label: string) {
    setConfigs((prev) => {
      const next = [...prev]
      const config = next[sheetIdx]
      if (!config) return prev
      next[sheetIdx] = {
        ...config,
        metadataColumns: config.metadataColumns.map((mc) =>
          mc.columnHeader === header ? { ...mc, label } : mc,
        ),
      }
      return next
    })
  }

  function goToSheet(nextIdx: number) {
    if (nextIdx < 0 || nextIdx >= sheets.length) return
    setConfigs((prev) => {
      const existing = prev[nextIdx]
      // Seed from the current sheet when the target is missing or still a
      // pristine empty config (never edited). This lets us pre-init all
      // sheets on mount while still carrying forward user choices when they
      // navigate to a fresh sheet.
      if (existing && !isPristine(existing)) return prev
      const next = [...prev]
      const prevConfig = prev[sheetIdx] || null
      next[nextIdx] = seedSheetConfig(prevConfig, sheets[nextIdx])
      return next
    })
    setSheetIdx(nextIdx)
    setPendingMetadataSelect(NOT_MAPPED)
  }

  const allSheetsValid =
    configs.length === sheets.length && configs.every(isSheetConfigValid)
  const currentValid = currentConfig ? isSheetConfigValid(currentConfig) : false
  const hasAnyUnskipped =
    configs.length > 0 && configs.some((c) => !c.skipped)

  const canContinue = allSheetsValid && hasAnyUnskipped && !loading

  function handleContinue() {
    if (!canContinue) return
    onNext({
      recordType: 'trait',
      sheets,
      sheetConfigs: configs,
    })
  }

  /** Build a preview of the first 3 mapped rows for the current sheet. */
  function getMappedPreview(): { headers: string[]; rows: string[][] } {
    if (!currentSheet || !currentConfig) return { headers: [], rows: [] }
    const enabledTraits = currentConfig.traitColumns.filter((tc) => tc.enabled)
    const previewHeaders: string[] = []
    if (currentConfig.plotNumberColumn) previewHeaders.push('Plot #')
    if (currentConfig.plotRowColumn) previewHeaders.push('Row')
    if (currentConfig.plotColumnColumn) previewHeaders.push('Col')
    if (currentConfig.accessionNameColumn) previewHeaders.push('Accession')
    if (currentConfig.lineNameColumn) previewHeaders.push('Line')
    if (currentConfig.aliasColumn) previewHeaders.push('Alias')
    for (const tc of enabledTraits) previewHeaders.push(tc.traitName || tc.columnHeader)
    for (const mc of currentConfig.metadataColumns) previewHeaders.push(`[${mc.label}]`)

    const previewRows: string[][] = currentSheet.rows.slice(0, 3).map((row) => {
      const r: string[] = []
      if (currentConfig.plotNumberColumn) {
        const v = row[currentConfig.plotNumberColumn]
        r.push(v != null ? String(v) : '')
      }
      if (currentConfig.plotRowColumn) {
        const v = row[currentConfig.plotRowColumn]
        r.push(v != null ? String(v) : '')
      }
      if (currentConfig.plotColumnColumn) {
        const v = row[currentConfig.plotColumnColumn]
        r.push(v != null ? String(v) : '')
      }
      if (currentConfig.accessionNameColumn) {
        const v = row[currentConfig.accessionNameColumn]
        r.push(v != null ? String(v).trim() : '')
      }
      if (currentConfig.lineNameColumn) {
        const v = row[currentConfig.lineNameColumn]
        r.push(v != null ? String(v).trim() : '')
      }
      if (currentConfig.aliasColumn) {
        const v = row[currentConfig.aliasColumn]
        r.push(v != null ? String(v).trim() : '')
      }
      for (const tc of enabledTraits) {
        const v = row[tc.columnHeader]
        r.push(v != null ? String(v) : '')
      }
      for (const mc of currentConfig.metadataColumns) {
        const v = row[mc.columnHeader]
        r.push(v != null ? String(v) : '')
      }
      return r
    })
    return { headers: previewHeaders, rows: previewRows }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Parsing spreadsheet...</p>
      </div>
    )
  }

  if (parseError) {
    return (
      <div className="space-y-6">
        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-4">
          <p className="text-sm text-destructive">{parseError}</p>
        </div>
        <div className="flex justify-between">
          <Button variant="outline" onClick={onBack}>
            Back
          </Button>
        </div>
      </div>
    )
  }

  if (!currentSheet || !currentConfig) return null

  const preview = getMappedPreview()

  return (
    <div className="space-y-6">
      {/* Current sheet indicator */}
      <div className="rounded-lg border p-4 flex items-center justify-between gap-3">
        <div className="text-sm">
          <span className="font-medium">
            Sheet {sheetIdx + 1} of {sheets.length}:
          </span>{' '}
          <span className="text-muted-foreground">
            {currentSheet.name} ({currentSheet.totalRows} rows)
          </span>
        </div>
        {sheets.length > 1 && (
          <label className="flex items-center gap-2 cursor-pointer text-sm">
            <input
              type="checkbox"
              checked={currentConfig.skipped}
              onChange={(e) => updateCurrentConfig({ skipped: e.target.checked })}
              className="accent-primary w-4 h-4"
              data-testid="sheet-skip"
            />
            Skip this sheet (don't import its data)
          </label>
        )}
      </div>

      {currentConfig.skipped && (
        <div className="rounded-md border border-dashed p-4 text-center text-sm text-muted-foreground">
          This sheet will be skipped during import. Uncheck above to configure it.
        </div>
      )}

      {!currentConfig.skipped && (
      <>
      {/* Data preview */}
      <div className="rounded-lg border p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">Data Preview</h3>
          <span className="text-xs text-muted-foreground">
            {currentSheet.totalRows} rows, {headers.length} columns
          </span>
        </div>
        <div className="overflow-x-auto max-h-64">
          <Table>
            <TableHeader>
              <TableRow>
                {headers.map((header) => (
                  <TableHead key={header} className="whitespace-nowrap">
                    {header}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {currentSheet.rows.slice(0, 5).map((row, i) => (
                <TableRow key={i}>
                  {headers.map((header) => (
                    <TableCell key={header} className="whitespace-nowrap">
                      {row[header] != null ? String(row[header]) : ''}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Plot columns — the primary row identifier */}
      <div className="rounded-lg border p-4 space-y-3">
        <div className="flex items-center gap-2">
          <h3 className="font-medium">Plot columns</h3>
          <Badge variant="destructive" className="text-[10px] px-1.5 py-0">
            Plot # required
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Trait records attach to plots. Plot number is required; plot row and
          column are optional.
        </p>
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="w-28 shrink-0 text-sm">Plot number *</div>
            <Select
              value={currentConfig.plotNumberColumn || NOT_MAPPED}
              onChange={(e) =>
                updateCurrentConfig({
                  plotNumberColumn:
                    e.target.value === NOT_MAPPED ? null : e.target.value,
                })
              }
              className="flex-1"
              data-testid="plot-number-select"
            >
              <option value={NOT_MAPPED}>-- Select a column --</option>
              {headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-28 shrink-0 text-sm">Plot row</div>
            <Select
              value={currentConfig.plotRowColumn || NOT_MAPPED}
              onChange={(e) =>
                updateCurrentConfig({
                  plotRowColumn:
                    e.target.value === NOT_MAPPED ? null : e.target.value,
                })
              }
              className="flex-1"
              data-testid="plot-row-select"
            >
              <option value={NOT_MAPPED}>-- Not mapped --</option>
              {headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-28 shrink-0 text-sm">Plot column</div>
            <Select
              value={currentConfig.plotColumnColumn || NOT_MAPPED}
              onChange={(e) =>
                updateCurrentConfig({
                  plotColumnColumn:
                    e.target.value === NOT_MAPPED ? null : e.target.value,
                })
              }
              className="flex-1"
              data-testid="plot-col-select"
            >
              <option value={NOT_MAPPED}>-- Not mapped --</option>
              {headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </Select>
          </div>
        </div>
      </div>

      {/* Trait columns */}
      <div className="rounded-lg border p-4 space-y-3">
        <div className="flex items-center gap-2">
          <h3 className="font-medium">Trait columns</h3>
          <Badge variant="destructive" className="text-[10px] px-1.5 py-0">
            Required
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Select every column that contains trait measurements. Each selected
          column becomes a separate trait. Edit the trait name and optionally
          specify its units (e.g., cm, count, g/m²).
        </p>
        <div className="space-y-2">
          {headers
            .filter((h) => !reservedColumns.has(h))
            .map((header) => {
              const entry = currentConfig.traitColumns.find(
                (tc) => tc.columnHeader === header,
              )
              const checked = entry?.enabled ?? false
              const label = entry?.traitName ?? header
              const units = entry?.units ?? ''
              return (
                <div key={header} className="flex items-center gap-3">
                  <label className="flex items-center gap-2 cursor-pointer w-48 shrink-0">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(e) => toggleTraitColumn(header, e.target.checked)}
                      className="accent-primary w-4 h-4"
                      data-testid={`trait-checkbox-${header}`}
                    />
                    <span className="text-sm font-medium truncate">{header}</span>
                  </label>
                  <Input
                    value={label}
                    onChange={(e) => updateTraitLabel(header, e.target.value)}
                    placeholder={header}
                    disabled={!checked}
                    className="flex-1"
                    data-testid={`trait-label-${header}`}
                  />
                  <Input
                    value={units}
                    onChange={(e) => updateTraitUnits(header, e.target.value)}
                    placeholder="units"
                    disabled={!checked}
                    className="w-28 shrink-0"
                    data-testid={`trait-units-${header}`}
                  />
                </div>
              )
            })}
          {headers.filter((h) => !reservedColumns.has(h)).length === 0 && (
            <p className="text-sm text-muted-foreground">
              All columns are being used for other roles. Clear a plot,
              genotype, timestamp, or metadata mapping to select it as a trait
              instead.
            </p>
          )}
        </div>
      </div>

      {/* Germplasm columns — accession, line, and alias roles */}
      <div className="rounded-lg border p-4 space-y-3">
        <h3 className="font-medium">Germplasm columns (optional)</h3>
        <p className="text-sm text-muted-foreground">
          Tag the columns that identify the germplasm for each row. An
          <em> accession </em> is a canonical germplasm unit (e.g.
          <code> SL-58-6-8-09</code>); a <em>line</em> is a pedigree anchor
          (e.g. <code>MAGIC110</code>, <code>B73</code>); an <em>alias</em> is
          a field-book shorthand (e.g. <code>1</code>, <code>Check1</code>)
          that points at an accession or line. You can map any combination —
          sheets often have a line name + a numeric alias, or an accession
          name on its own.
        </p>
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="w-36 shrink-0 text-sm">Accession name</div>
            <Select
              value={currentConfig.accessionNameColumn || NOT_MAPPED}
              onChange={(e) =>
                updateCurrentConfig({
                  accessionNameColumn:
                    e.target.value === NOT_MAPPED ? null : e.target.value,
                })
              }
              className="flex-1"
              data-testid="accession-name-column-select"
            >
              <option value={NOT_MAPPED}>-- Not mapped --</option>
              {headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-36 shrink-0 text-sm">Line name</div>
            <Select
              value={currentConfig.lineNameColumn || NOT_MAPPED}
              onChange={(e) =>
                updateCurrentConfig({
                  lineNameColumn:
                    e.target.value === NOT_MAPPED ? null : e.target.value,
                })
              }
              className="flex-1"
              data-testid="line-name-column-select"
            >
              <option value={NOT_MAPPED}>-- Not mapped --</option>
              {headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-36 shrink-0 text-sm">Alias</div>
            <Select
              value={currentConfig.aliasColumn || NOT_MAPPED}
              onChange={(e) =>
                updateCurrentConfig({
                  aliasColumn:
                    e.target.value === NOT_MAPPED ? null : e.target.value,
                })
              }
              className="flex-1"
              data-testid="alias-column-select"
            >
              <option value={NOT_MAPPED}>-- Not mapped --</option>
              {headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </Select>
          </div>
        </div>
      </div>

      {/* Optional: population name */}
      <PopulationField
        value={currentConfig.populationName}
        onChange={(v) => updateCurrentConfig({ populationName: v })}
        existing={(existingPopulations ?? []).map((p) => p.population_name).filter(Boolean) as string[]}
      />

      {/* Collection date */}
      <div className="rounded-lg border p-4 space-y-3">
        <h3 className="font-medium">Collection date</h3>
        <p className="text-sm text-muted-foreground">
          The date measurements were collected. Choose a fixed date, a column
          with per-row dates, or mark it unknown (e.g., for post-harvest
          measurements like yield with no meaningful collection date).
        </p>
        <div className="flex items-center gap-3">
          <Select
            value={currentConfig.collectionDateMode}
            onChange={(e) => {
              const mode = e.target.value as 'fixed' | 'column' | 'unknown'
              updateCurrentConfig({
                collectionDateMode: mode,
                ...(mode !== 'column' ? { collectionDateColumn: null } : {}),
                ...(mode !== 'fixed' ? { collectionDate: '' } : {}),
              })
            }}
            className="w-44 shrink-0"
            data-testid="collection-date-mode"
          >
            <option value="fixed">Fixed date</option>
            <option value="column">From column</option>
            <option value="unknown">Unknown / not defined</option>
          </Select>
          {currentConfig.collectionDateMode === 'fixed' && (
            <Input
              type="date"
              value={currentConfig.collectionDate}
              onChange={(e) => updateCurrentConfig({ collectionDate: e.target.value })}
              className="flex-1"
              data-testid="collection-date-fixed"
            />
          )}
          {currentConfig.collectionDateMode === 'column' && (
            <Select
              value={currentConfig.collectionDateColumn || NOT_MAPPED}
              onChange={(e) =>
                updateCurrentConfig({
                  collectionDateColumn:
                    e.target.value === NOT_MAPPED ? null : e.target.value,
                })
              }
              className="flex-1"
              data-testid="collection-date-column"
            >
              <option value={NOT_MAPPED}>-- Select a column --</option>
              {headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </Select>
          )}
        </div>
      </div>

      {/* Season */}
      <div className="rounded-lg border p-4 space-y-3">
        <div className="flex items-center gap-2">
          <h3 className="font-medium">Season</h3>
          <Badge variant="destructive" className="text-[10px] px-1.5 py-0">Required</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Specify a fixed season name for every row in this sheet, or read it
          from a column (useful when a sheet contains data from multiple years).
        </p>
        <div className="flex items-center gap-3">
          <Select
            value={currentConfig.seasonMode}
            onChange={(e) => {
              const mode = e.target.value as 'fixed' | 'column'
              updateCurrentConfig({
                seasonMode: mode,
                ...(mode === 'fixed' ? { seasonColumn: null } : { seasonName: '' }),
              })
            }}
            className="w-44 shrink-0"
            data-testid="season-mode"
          >
            <option value="fixed">Fixed value</option>
            <option value="column">From column</option>
          </Select>
          {currentConfig.seasonMode === 'fixed' ? (
            <Input
              value={currentConfig.seasonName}
              onChange={(e) => updateCurrentConfig({ seasonName: e.target.value })}
              placeholder="e.g. Summer 2022"
              className="flex-1"
              data-testid="season-fixed"
            />
          ) : (
            <Select
              value={currentConfig.seasonColumn || NOT_MAPPED}
              onChange={(e) =>
                updateCurrentConfig({
                  seasonColumn:
                    e.target.value === NOT_MAPPED ? null : e.target.value,
                })
              }
              className="flex-1"
              data-testid="season-column"
            >
              <option value={NOT_MAPPED}>-- Select a column --</option>
              {headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </Select>
          )}
        </div>
      </div>

      {/* Site */}
      <div className="rounded-lg border p-4 space-y-3">
        <div className="flex items-center gap-2">
          <h3 className="font-medium">Site</h3>
          <Badge variant="destructive" className="text-[10px] px-1.5 py-0">Required</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Specify a fixed site name for every row in this sheet, or read it
          from a column (useful when a sheet contains data from multiple locations).
        </p>
        <div className="flex items-center gap-3">
          <Select
            value={currentConfig.siteMode}
            onChange={(e) => {
              const mode = e.target.value as 'fixed' | 'column'
              updateCurrentConfig({
                siteMode: mode,
                ...(mode === 'fixed' ? { siteColumn: null } : { siteName: '' }),
              })
            }}
            className="w-44 shrink-0"
            data-testid="site-mode"
          >
            <option value="fixed">Fixed value</option>
            <option value="column">From column</option>
          </Select>
          {currentConfig.siteMode === 'fixed' ? (
            <Input
              value={currentConfig.siteName}
              onChange={(e) => updateCurrentConfig({ siteName: e.target.value })}
              placeholder="e.g. Davis Field A"
              className="flex-1"
              data-testid="site-fixed"
            />
          ) : (
            <Select
              value={currentConfig.siteColumn || NOT_MAPPED}
              onChange={(e) =>
                updateCurrentConfig({
                  siteColumn:
                    e.target.value === NOT_MAPPED ? null : e.target.value,
                })
              }
              className="flex-1"
              data-testid="site-column"
            >
              <option value={NOT_MAPPED}>-- Select a column --</option>
              {headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </Select>
          )}
        </div>
      </div>

      {/* Optional: timestamp */}
      <div className="rounded-lg border p-4 space-y-3">
        <h3 className="font-medium">Timestamp column (optional)</h3>
        <p className="text-sm text-muted-foreground">
          If unmapped, timestamps will be derived from the collection date.
        </p>
        <Select
          value={currentConfig.timestampColumn || NOT_MAPPED}
          onChange={(e) =>
            updateCurrentConfig({
              timestampColumn:
                e.target.value === NOT_MAPPED ? null : e.target.value,
            })
          }
          data-testid="timestamp-column-select"
        >
          <option value={NOT_MAPPED}>-- Not mapped --</option>
          {headers.map((header) => (
            <option key={header} value={header}>
              {header}
            </option>
          ))}
        </Select>
      </div>

      {/* Additional metadata columns */}
      <div className="rounded-lg border p-4 space-y-3">
        <h3 className="font-medium">Additional metadata (optional)</h3>
        <p className="text-sm text-muted-foreground">
          Add any other column as passthrough metadata. Each selected column is
          saved with every record under its label (e.g. notes, reps, block).
        </p>

        {currentConfig.metadataColumns.length > 0 && (
          <div className="space-y-2">
            {currentConfig.metadataColumns.map((mc) => (
              <div key={mc.columnHeader} className="flex items-center gap-3">
                <div className="w-36 shrink-0 text-sm truncate" title={mc.columnHeader}>
                  {mc.columnHeader}
                </div>
                <Input
                  value={mc.label}
                  onChange={(e) => updateMetadataLabel(mc.columnHeader, e.target.value)}
                  placeholder={mc.columnHeader}
                  className="flex-1"
                  data-testid={`metadata-label-${mc.columnHeader}`}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => removeMetadataColumn(mc.columnHeader)}
                  data-testid={`metadata-remove-${mc.columnHeader}`}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2">
          <Select
            value={pendingMetadataSelect}
            onChange={(e) => setPendingMetadataSelect(e.target.value)}
            className="flex-1"
            data-testid="metadata-add-select"
            disabled={availableForMetadata.length === 0}
          >
            <option value={NOT_MAPPED}>
              {availableForMetadata.length === 0
                ? '-- No columns available --'
                : '-- Choose a column to add --'}
            </option>
            {availableForMetadata.map((header) => (
              <option key={header} value={header}>
                {header}
              </option>
            ))}
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={() => addMetadataColumn(pendingMetadataSelect)}
            disabled={pendingMetadataSelect === NOT_MAPPED}
            data-testid="metadata-add-button"
          >
            <Plus className="w-4 h-4" />
            Add
          </Button>
        </div>
      </div>

      {/* Mapped preview */}
      {preview.headers.length > 0 && preview.rows.length > 0 && (
        <div className="rounded-lg border p-4 space-y-3">
          <h3 className="font-medium">Mapped Preview</h3>
          <p className="text-sm text-muted-foreground">
            How the first rows of this sheet will be interpreted:
          </p>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {preview.headers.map((label) => (
                    <TableHead key={label} className="whitespace-nowrap">
                      {label}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {preview.rows.map((row, i) => (
                  <TableRow key={i}>
                    {row.map((cell, j) => (
                      <TableCell key={j} className="whitespace-nowrap">
                        {cell}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      </>
      )}

      {/* Sheet navigation (only when multiple sheets) */}
      {sheets.length > 1 && (
        <div className="rounded-lg border p-3 flex items-center justify-between gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => goToSheet(sheetIdx - 1)}
            disabled={sheetIdx === 0}
            data-testid="sheet-prev"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous sheet
          </Button>
          <span className="text-sm text-muted-foreground">
            Sheet {sheetIdx + 1} of {sheets.length}
          </span>
          <Button
            // Highlight as the primary action when the user has finished
            // the current sheet but more sheets still need configuring —
            // makes it obvious that "Next sheet" is the step before
            // "Continue to Upload" becomes available.
            variant={currentValid && !canContinue && sheetIdx < sheets.length - 1 ? 'default' : 'outline'}
            size="sm"
            onClick={() => goToSheet(sheetIdx + 1)}
            disabled={sheetIdx === sheets.length - 1 || !currentValid}
            data-testid="sheet-next"
          >
            Next sheet
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} data-testid="mapping-back">
          Back
        </Button>
        <Button
          onClick={handleContinue}
          disabled={!canContinue}
          data-testid="mapping-continue"
        >
          Continue to Upload
        </Button>
      </div>
    </div>
  )
}
