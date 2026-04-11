import type { UploadResults } from '@/components/import-wizard/wizard-shell'
import { Button } from '@/components/ui/button'
import { useNavigate } from '@tanstack/react-router'
import { CheckCircle, XCircle, ArrowRight, RotateCcw } from 'lucide-react'

interface StepConfirmProps {
  results: UploadResults
  onDone: () => void
}

export function StepConfirm({ results, onDone }: StepConfirmProps) {
  const navigate = useNavigate()

  const hasErrors = results.failedFiles > 0
  const allFailed = results.uploadedFiles === 0 && results.failedFiles > 0

  return (
    <div className="space-y-6">
      {/* Success/warning banner */}
      <div className="flex flex-col items-center text-center py-8 space-y-3">
        {allFailed ? (
          <XCircle className="w-12 h-12 text-destructive" />
        ) : (
          <CheckCircle className="w-12 h-12 text-green-600" />
        )}
        <h2 className="text-xl font-semibold" data-testid="confirm-heading">
          {allFailed ? 'Import Failed' : hasErrors ? 'Import Completed with Errors' : 'Import Complete'}
        </h2>
        <p className="text-muted-foreground">
          {allFailed
            ? 'No files were uploaded successfully.'
            : `${results.uploadedFiles} file${results.uploadedFiles !== 1 ? 's' : ''} uploaded successfully.`}
          {hasErrors && !allFailed && ` ${results.failedFiles} file${results.failedFiles !== 1 ? 's' : ''} failed.`}
        </p>
      </div>

      {/* Created entities */}
      {results.createdEntities.length > 0 && (
        <div className="rounded-lg border p-4 space-y-3">
          <h3 className="font-medium">Created Entities</h3>
          <div className="space-y-1.5">
            {results.createdEntities.map((entity, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <CheckCircle className="w-3.5 h-3.5 text-green-600 shrink-0" />
                <span className="text-muted-foreground">{entity.type}:</span>
                <span className="font-medium">{entity.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload stats */}
      <div className="rounded-lg border p-4">
        <h3 className="font-medium mb-2">Upload Summary</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Files uploaded</span>
            <p className="text-lg font-semibold">{results.uploadedFiles}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Files failed</span>
            <p className="text-lg font-semibold">{results.failedFiles}</p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-center gap-3">
        <Button variant="outline" onClick={onDone} data-testid="import-more">
          <RotateCcw className="w-4 h-4 mr-1.5" />
          Import More
        </Button>
        {results.experimentId && (
          <Button
            data-testid="go-to-experiment"
            onClick={() =>
              navigate({ to: '/experiments/$experimentId', params: { experimentId: results.experimentId! } })
            }
          >
            Go to Experiment
            <ArrowRight className="w-4 h-4 ml-1.5" />
          </Button>
        )}
      </div>
    </div>
  )
}
