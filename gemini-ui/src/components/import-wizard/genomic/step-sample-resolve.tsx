import { useEffect, useMemo, useState } from 'react'
import type { FileWithPath } from '@/components/upload/dropzone'
import type { DetectionResult } from '@/components/import-wizard/detection-engine'
import type {
  GenomicMetadata,
  SampleResolution,
} from '@/components/import-wizard/genomic/genomic-wizard'
import {
  germplasmResolverApi,
  type ResolveResult,
} from '@/api/endpoints/germplasm-resolver'
import { readHapmapSampleHeaders } from '@/lib/hapmap-parser'
import { readVcfSampleHeaders } from '@/lib/vcf-parser'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import { CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react'

interface StepSampleResolveProps {
  detection: DetectionResult
  file: FileWithPath
  metadata: GenomicMetadata
  initial: SampleResolution | null
  onNext: (resolution: SampleResolution) => void
  onBack: () => void
}

type ResolutionState = {
  loading: boolean
  error: string | null
  /** Index-aligned with shape.sampleHeaders. */
  results: ResolveResult[]
  /** Headers that couldn't be auto-resolved. */
  unresolvedHeaders: string[]
}

export function StepSampleResolve({
  detection,
  file,
  metadata,
  initial,
  onNext,
  onBack,
}: StepSampleResolveProps) {
  const shape = detection.genomicShape!
  const [sampleHeaders, setSampleHeaders] = useState<string[]>(shape.sampleHeaders)
  const [resolutionState, setResolutionState] = useState<ResolutionState>({
    loading: true,
    error: null,
    results: [],
    unresolvedHeaders: [],
  })
  const [userChoice, setUserChoice] = useState<'skip_all' | 'create_all' | null>(
    initial ? (initial.createdAccessions.length > 0 ? 'create_all' : 'skip_all') : null,
  )

  // Matrix xlsx has sample headers already in the detection shape. HapMap and
  // VCF need a quick file read to pull the sample columns out of the header
  // line — the shape objects created at detection time for those formats use
  // `sampleHeaders: []` as a placeholder.
  useEffect(() => {
    let cancelled = false
    async function loadHeaders() {
      if (sampleHeaders.length > 0) return
      try {
        let headers: string[] = []
        if (shape.format === 'hapmap') headers = await readHapmapSampleHeaders(file as unknown as File)
        else if (shape.format === 'vcf') headers = await readVcfSampleHeaders(file as unknown as File)
        if (!cancelled) setSampleHeaders(headers)
      } catch (err) {
        if (!cancelled) {
          setResolutionState((prev) => ({
            ...prev,
            loading: false,
            error: err instanceof Error ? err.message : 'Failed to read sample headers',
          }))
        }
      }
    }
    loadHeaders()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (sampleHeaders.length === 0) return
    let cancelled = false
    async function resolve() {
      try {
        const res = await germplasmResolverApi.resolve({ names: sampleHeaders })
        if (cancelled) return
        const results = res.results ?? []
        const unresolved = results
          .filter((r) => r.match_kind === 'unresolved' || !r.canonical_name)
          .map((r) => r.input_name)
        setResolutionState({
          loading: false,
          error: null,
          results,
          unresolvedHeaders: unresolved,
        })
      } catch (err) {
        if (!cancelled) {
          setResolutionState({
            loading: false,
            error: err instanceof Error ? err.message : 'Resolver call failed',
            results: [],
            unresolvedHeaders: [],
          })
        }
      }
    }
    resolve()
    return () => {
      cancelled = true
    }
  }, [sampleHeaders])

  const { loading, error, results, unresolvedHeaders } = resolutionState

  const resolvedCount = results.length - unresolvedHeaders.length

  const previewRows = useMemo(() => results.slice(0, 25), [results])

  const canContinue = !loading &&
    !error &&
    results.length > 0 &&
    (unresolvedHeaders.length === 0 || userChoice !== null)

  async function handleContinue() {
    if (!canContinue) return
    const canonicalByHeader: Record<string, string> = {}
    const skippedHeaders = new Set<string>()
    const createdAccessions: string[] = []

    for (const r of results) {
      const raw = r.input_name
      if (r.canonical_name && r.match_kind !== 'unresolved') {
        canonicalByHeader[raw] = r.canonical_name
        continue
      }
      if (userChoice === 'skip_all') {
        skippedHeaders.add(raw)
      } else if (userChoice === 'create_all') {
        // Register the name itself as the canonical accession. Actual
        // accession creation happens in step-ingest-genomic, after we've
        // confirmed the study and right before we need the records.
        canonicalByHeader[raw] = raw
        createdAccessions.push(raw)
      }
    }

    onNext({ canonicalByHeader, skippedHeaders, createdAccessions })
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border p-4 space-y-2" data-testid="sample-resolve-summary">
        <h3 className="font-medium">Sample Resolution</h3>
        <p className="text-sm text-muted-foreground">
          Matching the <strong>{sampleHeaders.length}</strong> sample columns in{' '}
          <code>{file.name}</code> against existing accessions
          {metadata.experimentName && <> in experiment <code>{metadata.experimentName}</code></>}.
        </p>
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" /> Resolving...
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertTriangle className="w-4 h-4" /> {error}
          </div>
        ) : (
          <div className="flex items-center gap-3 text-sm">
            <CheckCircle2 className="w-4 h-4 text-green-600" />
            <span><strong>{resolvedCount}</strong> of {results.length} resolved automatically</span>
            {unresolvedHeaders.length > 0 && (
              <Badge variant="outline">{unresolvedHeaders.length} unresolved</Badge>
            )}
          </div>
        )}
      </div>

      {!loading && !error && unresolvedHeaders.length > 0 && (
        <div className="rounded-lg border p-4 space-y-3" data-testid="unresolved-action">
          <h4 className="font-medium">How should we handle the {unresolvedHeaders.length} unresolved sample headers?</h4>
          <p className="text-sm text-muted-foreground">
            Unresolved headers are sample IDs we couldn't match to an existing
            accession. You can skip them (drop their genotype calls from the
            import) or auto-create an accession for each.
          </p>
          <div className="flex gap-2">
            <Button
              variant={userChoice === 'skip_all' ? 'default' : 'outline'}
              onClick={() => setUserChoice('skip_all')}
              data-testid="unresolved-skip-all"
            >
              Skip all {unresolvedHeaders.length}
            </Button>
            <Button
              variant={userChoice === 'create_all' ? 'default' : 'outline'}
              onClick={() => setUserChoice('create_all')}
              data-testid="unresolved-create-all"
            >
              Auto-create accessions for all
            </Button>
          </div>
          <details className="text-sm">
            <summary className="cursor-pointer text-muted-foreground">
              Show unresolved sample names
            </summary>
            <div className="mt-2 flex flex-wrap gap-1 max-h-48 overflow-y-auto">
              {unresolvedHeaders.map((name) => (
                <Badge key={name} variant="secondary" className="text-xs">{name}</Badge>
              ))}
            </div>
          </details>
        </div>
      )}

      {!loading && !error && results.length > 0 && (
        <div className="rounded-md border overflow-hidden" data-testid="sample-resolve-preview">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Sample header</TableHead>
                <TableHead>Match</TableHead>
                <TableHead>Canonical name</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {previewRows.map((r) => (
                <TableRow key={r.input_name}>
                  <TableCell className="font-mono text-xs">{r.input_name}</TableCell>
                  <TableCell>
                    <Badge
                      variant={r.match_kind === 'unresolved' ? 'outline' : 'secondary'}
                      className="text-xs"
                    >
                      {r.match_kind}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs">{r.canonical_name ?? <span className="text-muted-foreground">—</span>}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {results.length > previewRows.length && (
            <div className="border-t p-2 text-xs text-muted-foreground text-center">
              Showing first {previewRows.length} of {results.length} samples
            </div>
          )}
        </div>
      )}

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>Back</Button>
        <Button
          onClick={handleContinue}
          disabled={!canContinue}
          data-testid="sample-resolve-continue"
        >
          Continue
        </Button>
      </div>
    </div>
  )
}
