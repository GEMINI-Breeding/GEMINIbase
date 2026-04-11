import { useState, useEffect, useMemo } from 'react'
import type { FileWithPath } from '@/components/upload/dropzone'
import type {
  ColumnMapping,
  SheetMapping,
  TraitColumn,
  MetadataColumn,
} from '@/components/import-wizard/wizard-shell'
import { parseSpreadsheet, type ParsedSheet } from '@/lib/spreadsheet-parser'
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
  onNext: (mapping: ColumnMapping) => void
  onBack: () => void
}

const NOT_MAPPED = '__not_mapped__'

function emptySheetConfig(sheet: ParsedSheet): SheetMapping {
  return {
    sheetName: sheet.name,
    plotNumberColumn: null,
    plotRowColumn: null,
    plotColumnColumn: null,
    traitColumns: [],
    genotypeColumn: null,
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
    plotNumberColumn: copyIfPresent(prev.plotNumberColumn),
    plotRowColumn: copyIfPresent(prev.plotRowColumn),
    plotColumnColumn: copyIfPresent(prev.plotColumnColumn),
    traitColumns: prev.traitColumns
      .filter((tc) => headerSet.has(tc.columnHeader))
      .map((tc) => ({ ...tc })),
    genotypeColumn: copyIfPresent(prev.genotypeColumn),
    timestampColumn: copyIfPresent(prev.timestampColumn),
    metadataColumns: prev.metadataColumns
      .filter((mc) => headerSet.has(mc.columnHeader))
      .map((mc) => ({ ...mc })),
  }
}

function isSheetConfigValid(config: SheetMapping): boolean {
  // Plot number is the primary row identifier — required.
  if (!config.plotNumberColumn) return false
  // At least one enabled trait column with a non-empty label.
  const enabledTraits = config.traitColumns.filter((tc) => tc.enabled)
  if (enabledTraits.length === 0) return false
  if (!enabledTraits.every((tc) => tc.traitName.trim() !== '')) return false
  // Every metadata column needs a non-empty label.
  if (!config.metadataColumns.every((mc) => mc.label.trim() !== '')) return false
  return true
}

export function StepColumnMapping({
  files,
  onNext,
  onBack,
}: StepColumnMappingProps) {
  const [sheets, setSheets] = useState<ParsedSheet[]>([])
  const [loading, setLoading] = useState(true)
  const [parseError, setParseError] = useState<string | null>(null)
  const [sheetIdx, setSheetIdx] = useState(0)
  const [configs, setConfigs] = useState<SheetMapping[]>([])
  const [pendingMetadataSelect, setPendingMetadataSelect] = useState<string>(NOT_MAPPED)

  // Parse spreadsheet files on mount
  useEffect(() => {
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
        setConfigs([emptySheetConfig(parsed[0])])
      } catch (err) {
        setParseError(
          err instanceof Error ? err.message : 'Failed to parse file.',
        )
      } finally {
        setLoading(false)
      }
    }
    parse()
  }, [files])

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
    if (currentConfig.genotypeColumn) s.add(currentConfig.genotypeColumn)
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
          { columnHeader: header, traitName: header, enabled },
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
      if (prev[nextIdx]) return prev
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

  const isLastSheet = sheetIdx === sheets.length - 1
  const canContinue = isLastSheet && allSheetsValid && !loading

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
    if (currentConfig.genotypeColumn) previewHeaders.push('Genotype')
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
      if (currentConfig.genotypeColumn) {
        const v = row[currentConfig.genotypeColumn]
        r.push(v != null ? String(v) : '')
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
      {/* Sheet navigation header */}
      <div className="rounded-lg border p-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
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
          <Button
            variant="outline"
            size="sm"
            onClick={() => goToSheet(sheetIdx + 1)}
            disabled={sheetIdx === sheets.length - 1 || !currentValid}
            data-testid="sheet-next"
          >
            Next sheet
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
        <div className="text-sm">
          <span className="font-medium">
            Sheet {sheetIdx + 1} of {sheets.length}:
          </span>{' '}
          <span className="text-muted-foreground">
            {currentSheet.name} ({currentSheet.totalRows} rows)
          </span>
        </div>
      </div>

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
          column becomes a separate trait. You can edit the label that will be
          used as the trait name.
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

      {/* Optional: genotype */}
      <div className="rounded-lg border p-4 space-y-3">
        <h3 className="font-medium">Genotype column (optional)</h3>
        <p className="text-sm text-muted-foreground">
          If the sheet has an accession/genotype column, map it here. Its value
          is saved with each trait record as metadata.
        </p>
        <Select
          value={currentConfig.genotypeColumn || NOT_MAPPED}
          onChange={(e) =>
            updateCurrentConfig({
              genotypeColumn:
                e.target.value === NOT_MAPPED ? null : e.target.value,
            })
          }
          data-testid="genotype-column-select"
        >
          <option value={NOT_MAPPED}>-- Not mapped --</option>
          {headers.map((header) => (
            <option key={header} value={header}>
              {header}
            </option>
          ))}
        </Select>
      </div>

      {/* Optional: timestamp */}
      <div className="rounded-lg border p-4 space-y-3">
        <h3 className="font-medium">Timestamp column (optional)</h3>
        <p className="text-sm text-muted-foreground">
          If unmapped, timestamps will be auto-generated using the current
          time.
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
