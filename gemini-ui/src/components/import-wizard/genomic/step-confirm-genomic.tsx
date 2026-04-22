import { useNavigate } from '@tanstack/react-router'
import type { IngestResult } from '@/components/import-wizard/genomic/genomic-wizard'
import { Button } from '@/components/ui/button'
import { CheckCircle, XCircle, ArrowRight, RotateCcw } from 'lucide-react'

interface StepConfirmGenomicProps {
  result: IngestResult
  onDone: () => void
}

export function StepConfirmGenomic({ result, onDone }: StepConfirmGenomicProps) {
  const navigate = useNavigate()
  const hasErrors = result.errors.length > 0
  const anythingInserted = result.variantsInserted > 0 || result.recordsInserted > 0

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center text-center py-8 space-y-3">
        {anythingInserted ? (
          <CheckCircle className="w-12 h-12 text-green-600" />
        ) : (
          <XCircle className="w-12 h-12 text-destructive" />
        )}
        <h2 className="text-xl font-semibold" data-testid="genomic-confirm-heading">
          {anythingInserted ? 'Genomic Import Complete' : 'Nothing Imported'}
        </h2>
        <p className="text-muted-foreground">
          Study <span className="font-medium">{result.studyName}</span>
        </p>
      </div>

      <div className="rounded-lg border p-4">
        <h3 className="font-medium mb-3">Ingest Summary</h3>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <Stat label="Variants inserted" value={result.variantsInserted} />
          <Stat label="Genotype records inserted" value={result.recordsInserted} />
          <Stat label="Batches sent" value={result.batchesRun} />
        </div>
        {result.rawObjectName && (
          <p className="text-xs text-muted-foreground mt-3">
            Raw file archived at <code>{result.rawObjectName}</code>
          </p>
        )}
      </div>

      {hasErrors && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm">
          <p className="font-medium text-destructive mb-1">
            Server reported {result.errors.length} warning{result.errors.length === 1 ? '' : 's'}
          </p>
          <ul className="list-disc pl-5 space-y-0.5 max-h-48 overflow-y-auto">
            {result.errors.slice(0, 100).map((e, i) => (
              <li key={i} className="text-xs">{e}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex justify-center gap-3">
        <Button variant="outline" onClick={onDone} data-testid="genomic-import-more">
          <RotateCcw className="w-4 h-4 mr-1.5" />
          Import More
        </Button>
        <Button
          data-testid="go-to-study"
          onClick={() =>
            navigate({ to: '/genotyping-studies/$studyId', params: { studyId: result.studyId } })
          }
        >
          View Study
          <ArrowRight className="w-4 h-4 ml-1.5" />
        </Button>
      </div>
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
