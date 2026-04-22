import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type {
  ColumnMapping,
  GermplasmReview,
  ImportMetadata,
  SheetMapping,
} from '@/components/import-wizard/wizard-shell'
import {
  germplasmResolverApi,
  normalizeGermplasmName,
  type ResolveResult,
  type AliasBulkEntry,
} from '@/api/endpoints/germplasm-resolver'
import { accessionsApi } from '@/api/endpoints/accessions'
import { linesApi } from '@/api/endpoints/lines'
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
import { Loader2, CheckCircle2, AlertTriangle } from 'lucide-react'

interface StepGermplasmReviewProps {
  mapping: ColumnMapping
  metadata: ImportMetadata
  initial: GermplasmReview | null
  onNext: (review: GermplasmReview) => void
  onBack: () => void
}

type DecisionKind = 'skip' | 'create_accession' | 'create_line' | 'link_accession' | 'link_line'

interface Decision {
  kind: DecisionKind
  /** For create_* kinds, the new canonical name to POST. */
  newName: string
  /** For link_* kinds, the UUID of the target. */
  linkId: string
  /** For link_* kinds, display name of the selected target. */
  linkName: string
  /** For link_* / create_alias-backed kinds, whether to persist this
   *  resolution as an experiment-scoped alias. */
  recordAsAlias: boolean
}

function defaultDecision(): Decision {
  return {
    kind: 'create_accession',
    newName: '',
    linkId: '',
    linkName: '',
    recordAsAlias: true,
  }
}

/**
 * Walk every mapped sheet and return the set of unique germplasm names the
 * user wants us to resolve. A name is any cell value from accessionNameColumn,
 * lineNameColumn, or aliasColumn; duplicates and empty strings are dropped.
 */
function collectGermplasmNames(mapping: ColumnMapping): string[] {
  const set = new Set<string>()
  for (let i = 0; i < mapping.sheets.length; i++) {
    const sheet = mapping.sheets[i]
    const config: SheetMapping | undefined = mapping.sheetConfigs[i]
    if (!config || config.skipped) continue
    const cols = [
      config.accessionNameColumn,
      config.lineNameColumn,
      config.aliasColumn,
    ].filter((c): c is string => !!c)
    if (cols.length === 0) continue
    for (const row of sheet.rows) {
      for (const col of cols) {
        const v = row[col]
        if (v == null) continue
        const trimmed = normalizeGermplasmName(String(v))
        if (trimmed) set.add(trimmed)
      }
    }
  }
  return Array.from(set)
}

/** Pick a reasonable default decision given what the resolver told us.
 *  Unresolved values default to "create a new accession with this exact
 *  name" — the common case for a fresh DB where the spreadsheet carries
 *  the canonical names (e.g. MAGIC110) rather than typos. The user can
 *  still override per row, and the "Save as alias" checkbox is off for
 *  this case since input_name == canonical_name. */
function seedDecision(result: ResolveResult): Decision {
  const d = defaultDecision()
  if (result.match_kind === 'unresolved') {
    d.kind = 'create_accession'
    d.newName = result.input_name
    d.recordAsAlias = false
  }
  return d
}

function kindSummary(r: ResolveResult): string {
  switch (r.match_kind) {
    case 'accession_exact': return 'Accession (exact match)'
    case 'line_exact':      return 'Line (exact match)'
    case 'alias_experiment':return 'Alias (this experiment)'
    case 'alias_global':    return 'Alias (global)'
    case 'unresolved':      return 'Unresolved'
    default:                return r.match_kind
  }
}

function kindBadgeVariant(kind: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (kind === 'unresolved') return 'destructive'
  if (kind.startsWith('alias')) return 'secondary'
  return 'default'
}

export function StepGermplasmReview({
  mapping,
  metadata,
  initial,
  onNext,
  onBack,
}: StepGermplasmReviewProps) {
  const names = useMemo(() => initial?.allNames ?? collectGermplasmNames(mapping), [mapping, initial])
  const experimentId = metadata.experimentId || null

  const {
    data: resolution,
    isLoading,
    error: resolveError,
  } = useQuery({
    queryKey: ['germplasm-resolve', experimentId, names],
    queryFn: () =>
      germplasmResolverApi.resolve({
        names,
        experiment_id: experimentId,
      }),
    enabled: names.length > 0,
  })

  // Load existing accessions + lines for the "link to existing" picker.
  // 500 is plenty for typical breeding programs; if a program has more, we
  // can switch to a searchable async picker in a follow-up.
  const { data: existingAccessions } = useQuery({
    queryKey: ['accessions', 'all'],
    queryFn: () => accessionsApi.getAll(500, 0),
  })
  const { data: existingLines } = useQuery({
    queryKey: ['lines', 'all'],
    queryFn: () => linesApi.getAll(500, 0),
  })

  // Per-unresolved-input decision state.
  const [decisions, setDecisions] = useState<Record<string, Decision>>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitProgress, setSubmitProgress] = useState<{ done: number; total: number } | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // Seed decisions from resolver output when it arrives. Preserve any
  // existing decisions so navigating back/forward doesn't wipe user edits.
  useEffect(() => {
    if (!resolution) return
    setDecisions((prev) => {
      const next = { ...prev }
      for (const r of resolution.results) {
        if (r.match_kind !== 'unresolved') continue
        if (!next[r.input_name]) next[r.input_name] = seedDecision(r)
      }
      return next
    })
  }, [resolution])

  const resolvedResults = resolution?.results ?? []
  const resolvedCount = resolvedResults.filter((r) => r.match_kind !== 'unresolved').length
  const unresolved = resolvedResults.filter((r) => r.match_kind === 'unresolved')
  /** Hundreds of rows in a single table trashes the scroll position and
   *  makes the wizard feel unresponsive. Paginate at 100; the user can
   *  bulk-apply above to avoid needing to individually inspect each. */
  const UNRESOLVED_DISPLAY_LIMIT = 100
  const displayedUnresolved = unresolved.slice(0, UNRESOLVED_DISPLAY_LIMIT)
  const hiddenUnresolvedCount = Math.max(0, unresolved.length - UNRESOLVED_DISPLAY_LIMIT)

  function setDecision(inputName: string, patch: Partial<Decision>) {
    setDecisions((prev) => ({
      ...prev,
      [inputName]: { ...(prev[inputName] ?? defaultDecision()), ...patch },
    }))
  }

  /**
   * Apply a bulk action to every unresolved row. Useful when the sheet is
   * hundreds of rows and each row has the same shape (e.g. MAGIC sheet:
   * 300 canonical line names that all should become new lines).
   */
  function applyBulk(kind: 'create_accession' | 'create_line' | 'skip') {
    setDecisions((prev) => {
      const next = { ...prev }
      for (const r of unresolved) {
        const existing = next[r.input_name] ?? defaultDecision()
        if (kind === 'skip') {
          next[r.input_name] = { ...existing, kind: 'skip' }
        } else {
          next[r.input_name] = {
            ...existing,
            kind,
            newName: r.input_name,
            recordAsAlias: false,
          }
        }
      }
      return next
    })
  }

  /**
   * Every unresolved row must have a complete decision before Continue is
   * enabled. We stay strict here — silently accepting half-configured rows
   * is exactly the typo-sneaking-through failure the review step exists to
   * prevent.
   */
  const allDecided = useMemo(() => {
    for (const r of unresolved) {
      const d = decisions[r.input_name]
      if (!d) return false
      if (d.kind === 'skip') continue
      if (d.kind === 'create_accession' || d.kind === 'create_line') {
        if (!d.newName.trim()) return false
      } else if (d.kind === 'link_accession' || d.kind === 'link_line') {
        if (!d.linkId) return false
      }
    }
    return true
  }, [unresolved, decisions])

  async function handleContinue() {
    if (submitting) return
    setSubmitError(null)

    // 1) Create any new accessions/lines the user asked for.
    // 2) Collect alias entries the user opted to record.
    // 3) POST /aliases/bulk so subsequent imports (and the upload step) can
    //    resolve the same names without re-asking.
    const aliasEntries: AliasBulkEntry[] = []
    const resolvedMap: GermplasmReview['resolved'] = {}

    // Pre-seed with the rows the backend already resolved cleanly.
    for (const r of resolvedResults) {
      if (r.match_kind !== 'unresolved') {
        resolvedMap[r.input_name] = {
          match_kind: r.match_kind,
          accession_id: r.accession_id ?? null,
          line_id: r.line_id ?? null,
          canonical_name: r.canonical_name ?? null,
        }
      }
    }

    setSubmitting(true)
    setSubmitProgress({ done: 0, total: unresolved.length })
    try {
      // Run ~8 creates in flight to keep latency-bound sheets (300+ rows)
      // from taking minutes. Individual failures are propagated — an
      // alias-conflict response comes back on the bulk call below, but an
      // accession/line create failure here aborts the submit.
      const CONCURRENCY = 8
      let index = 0
      let done = 0
      const resolvedEntries: Array<[string, GermplasmReview['resolved'][string]]> = []
      const localAliasEntries: AliasBulkEntry[] = []

      async function processOne(r: ResolveResult) {
        const d = decisions[r.input_name]
        if (!d || d.kind === 'skip') {
          resolvedEntries.push([r.input_name, { match_kind: 'unresolved', canonical_name: null }])
          return
        }
        if (d.kind === 'create_accession') {
          const created = await accessionsApi.create({
            accession_name: normalizeGermplasmName(d.newName),
          })
          resolvedEntries.push([
            r.input_name,
            {
              match_kind: 'accession_exact',
              accession_id: String(created.id ?? ''),
              canonical_name: created.accession_name ?? d.newName,
            },
          ])
          if (
            d.recordAsAlias &&
            normalizeGermplasmName(r.input_name) !== normalizeGermplasmName(d.newName)
          ) {
            localAliasEntries.push({
              alias: r.input_name,
              accession_name: created.accession_name ?? d.newName,
              source: 'wizard:review',
            })
          }
        } else if (d.kind === 'create_line') {
          const created = await linesApi.create({
            line_name: normalizeGermplasmName(d.newName),
          })
          resolvedEntries.push([
            r.input_name,
            {
              match_kind: 'line_exact',
              line_id: String(created.id ?? ''),
              canonical_name: created.line_name ?? d.newName,
            },
          ])
          if (
            d.recordAsAlias &&
            normalizeGermplasmName(r.input_name) !== normalizeGermplasmName(d.newName)
          ) {
            localAliasEntries.push({
              alias: r.input_name,
              line_name: created.line_name ?? d.newName,
              source: 'wizard:review',
            })
          }
        } else if (d.kind === 'link_accession') {
          resolvedEntries.push([
            r.input_name,
            {
              match_kind: 'alias_experiment',
              accession_id: d.linkId,
              canonical_name: d.linkName,
            },
          ])
          if (d.recordAsAlias) {
            localAliasEntries.push({
              alias: r.input_name,
              accession_name: d.linkName,
              source: 'wizard:review',
            })
          }
        } else if (d.kind === 'link_line') {
          resolvedEntries.push([
            r.input_name,
            {
              match_kind: 'alias_experiment',
              line_id: d.linkId,
              canonical_name: d.linkName,
            },
          ])
          if (d.recordAsAlias) {
            localAliasEntries.push({
              alias: r.input_name,
              line_name: d.linkName,
              source: 'wizard:review',
            })
          }
        }
      }

      async function pump() {
        while (index < unresolved.length) {
          const i = index++
          await processOne(unresolved[i])
          done++
          setSubmitProgress({ done, total: unresolved.length })
        }
      }
      await Promise.all(
        Array.from({ length: Math.min(CONCURRENCY, unresolved.length) }, () => pump()),
      )

      for (const [k, v] of resolvedEntries) resolvedMap[k] = v
      aliasEntries.push(...localAliasEntries)

      if (aliasEntries.length > 0) {
        const scope: 'global' | 'experiment' = experimentId ? 'experiment' : 'global'
        const resp = await germplasmResolverApi.bulkAliases({
          scope,
          experiment_id: scope === 'experiment' ? experimentId : null,
          entries: aliasEntries,
        })
        // Surface conflict errors but don't block — the user already chose
        // a target, and a conflicting alias is a future-import concern,
        // not a blocker for this one.
        if (resp.errors.length > 0) {
          setSubmitError(
            `Some aliases were not saved (${resp.errors.length} conflict${resp.errors.length > 1 ? 's' : ''}). ` +
            `First: ${resp.errors[0].alias}: ${resp.errors[0].reason}`,
          )
        }
      }

      onNext({
        allNames: names,
        resolved: resolvedMap,
      })
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : String(e))
    } finally {
      setSubmitting(false)
    }
  }

  // Degenerate case: the user mapped no germplasm columns at all. The shell
  // should skip this step entirely, but guard just in case.
  if (names.length === 0) {
    return (
      <div className="space-y-6">
        <div className="rounded-md border p-4 text-sm text-muted-foreground">
          No germplasm columns were mapped — nothing to review. Click Continue
          to proceed.
        </div>
        <div className="flex justify-between">
          <Button variant="outline" onClick={onBack}>Back</Button>
          <Button
            onClick={() => onNext({ allNames: [], resolved: {} })}
            data-testid="germplasm-review-continue"
          >
            Continue to Upload
          </Button>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">
          Resolving {names.length} germplasm name{names.length === 1 ? '' : 's'}…
        </p>
      </div>
    )
  }

  if (resolveError) {
    return (
      <div className="space-y-6">
        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-4">
          <p className="text-sm text-destructive">
            Failed to resolve germplasm names:{' '}
            {resolveError instanceof Error ? resolveError.message : String(resolveError)}
          </p>
        </div>
        <div className="flex justify-between">
          <Button variant="outline" onClick={onBack}>Back</Button>
        </div>
      </div>
    )
  }

  const accessionOptions =
    (existingAccessions ?? [])
      .filter((a) => a.accession_name && a.id)
      .map((a) => ({ id: String(a.id), name: a.accession_name! }))
  const lineOptions =
    (existingLines ?? [])
      .filter((l) => l.line_name && l.id)
      .map((l) => ({ id: String(l.id), name: l.line_name! }))

  return (
    <div className="space-y-6">
      {/* Summary banner */}
      <div className="rounded-lg border p-4 flex items-center gap-3">
        {unresolved.length === 0 ? (
          <>
            <CheckCircle2 className="w-5 h-5 text-primary" />
            <div className="text-sm">
              <span className="font-medium">
                All {names.length} germplasm name{names.length === 1 ? '' : 's'} resolved.
              </span>{' '}
              <span className="text-muted-foreground">
                Nothing to review — click Continue to upload.
              </span>
            </div>
          </>
        ) : (
          <>
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <div className="text-sm">
              <span className="font-medium">
                {resolvedCount} / {names.length} resolved.
              </span>{' '}
              <span className="text-muted-foreground">
                {unresolved.length} need{unresolved.length === 1 ? 's' : ''} a decision below.
              </span>
            </div>
          </>
        )}
      </div>

      {/* Unresolved rows — action table */}
      {unresolved.length > 0 && (
        <div className="rounded-lg border p-4 space-y-3">
          <h3 className="font-medium">Unresolved germplasm</h3>
          <p className="text-sm text-muted-foreground">
            For each name below, choose how it should be resolved. Creating a
            new entity makes a canonical record; linking attaches the
            spreadsheet value as an alias for an existing accession or line.
            By default every unresolved row is set to "Create new accession"
            with the spreadsheet value as the canonical name — fine for a
            fresh database where the sheet holds the authoritative names.
          </p>
          <div className="flex flex-wrap items-center gap-2 border-b pb-3">
            <span className="text-sm font-medium mr-1">Apply to all {unresolved.length}:</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => applyBulk('create_accession')}
              data-testid="bulk-create-accession"
            >
              Create as accessions
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => applyBulk('create_line')}
              data-testid="bulk-create-line"
            >
              Create as lines
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => applyBulk('skip')}
              data-testid="bulk-skip"
            >
              Skip all
            </Button>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-48">Spreadsheet value</TableHead>
                <TableHead className="w-48">Action</TableHead>
                <TableHead>Target</TableHead>
                <TableHead className="w-36">Save as alias?</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayedUnresolved.map((r) => {
                const d = decisions[r.input_name] ?? defaultDecision()
                return (
                  <TableRow key={r.input_name}>
                    <TableCell className="font-mono text-sm">{r.input_name}</TableCell>
                    <TableCell>
                      <Select
                        value={d.kind}
                        onChange={(e) =>
                          setDecision(r.input_name, { kind: e.target.value as DecisionKind })
                        }
                        data-testid={`decision-kind-${r.input_name}`}
                      >
                        <option value="create_accession">Create new accession</option>
                        <option value="create_line">Create new line</option>
                        <option value="link_accession">Link to existing accession</option>
                        <option value="link_line">Link to existing line</option>
                        <option value="skip">Skip (leave unresolved)</option>
                      </Select>
                    </TableCell>
                    <TableCell>
                      {(d.kind === 'create_accession' || d.kind === 'create_line') && (
                        <Input
                          value={d.newName}
                          onChange={(e) => setDecision(r.input_name, { newName: e.target.value })}
                          placeholder="Canonical name"
                          data-testid={`decision-newname-${r.input_name}`}
                        />
                      )}
                      {d.kind === 'link_accession' && (
                        <Select
                          value={d.linkId}
                          onChange={(e) => {
                            const opt = accessionOptions.find((o) => o.id === e.target.value)
                            setDecision(r.input_name, {
                              linkId: e.target.value,
                              linkName: opt?.name ?? '',
                            })
                          }}
                          data-testid={`decision-linkacc-${r.input_name}`}
                        >
                          <option value="">-- Select accession --</option>
                          {accessionOptions.map((opt) => (
                            <option key={opt.id} value={opt.id}>
                              {opt.name}
                            </option>
                          ))}
                        </Select>
                      )}
                      {d.kind === 'link_line' && (
                        <Select
                          value={d.linkId}
                          onChange={(e) => {
                            const opt = lineOptions.find((o) => o.id === e.target.value)
                            setDecision(r.input_name, {
                              linkId: e.target.value,
                              linkName: opt?.name ?? '',
                            })
                          }}
                          data-testid={`decision-linkline-${r.input_name}`}
                        >
                          <option value="">-- Select line --</option>
                          {lineOptions.map((opt) => (
                            <option key={opt.id} value={opt.id}>
                              {opt.name}
                            </option>
                          ))}
                        </Select>
                      )}
                      {d.kind === 'skip' && (
                        <span className="text-xs text-muted-foreground">
                          Rows referencing this will import without a germplasm link.
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      {d.kind !== 'skip' && (
                        <label className="flex items-center gap-2 cursor-pointer text-sm">
                          <input
                            type="checkbox"
                            checked={d.recordAsAlias}
                            onChange={(e) =>
                              setDecision(r.input_name, { recordAsAlias: e.target.checked })
                            }
                            className="accent-primary w-4 h-4"
                            data-testid={`decision-alias-${r.input_name}`}
                          />
                          {experimentId ? 'In this experiment' : 'Globally'}
                        </label>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          {hiddenUnresolvedCount > 0 && (
            <p className="text-xs text-muted-foreground">
              Showing {displayedUnresolved.length} of {unresolved.length} unresolved values.
              The remaining {hiddenUnresolvedCount} will use whatever bulk default you
              apply above.
            </p>
          )}
        </div>
      )}

      {/* Resolved rows — confirmation table, collapsed by default for long lists */}
      {resolvedCount > 0 && (
        <details className="rounded-lg border p-4">
          <summary className="font-medium cursor-pointer">
            Resolved ({resolvedCount})
          </summary>
          <div className="mt-3 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Spreadsheet value</TableHead>
                  <TableHead>Canonical name</TableHead>
                  <TableHead>How</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {resolvedResults
                  .filter((r) => r.match_kind !== 'unresolved')
                  .map((r) => (
                    <TableRow key={r.input_name}>
                      <TableCell className="font-mono text-sm">{r.input_name}</TableCell>
                      <TableCell>{r.canonical_name ?? '—'}</TableCell>
                      <TableCell>
                        <Badge variant={kindBadgeVariant(r.match_kind)} className="text-[10px]">
                          {kindSummary(r)}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>
        </details>
      )}

      {submitError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-3 text-sm text-destructive">
          {submitError}
        </div>
      )}

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} disabled={submitting} data-testid="germplasm-review-back">
          Back
        </Button>
        <Button
          onClick={handleContinue}
          disabled={submitting || !allDecided}
          data-testid="germplasm-review-continue"
        >
          {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
          {submitting && submitProgress
            ? `Creating germplasm (${submitProgress.done}/${submitProgress.total})…`
            : 'Continue to Upload'}
        </Button>
      </div>
    </div>
  )
}
