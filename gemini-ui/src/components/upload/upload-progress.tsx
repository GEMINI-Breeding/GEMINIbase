import type { UploadState } from '@/hooks/use-upload'
import { cn } from '@/lib/utils'
import { CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { formatFileSize } from '@/components/import-wizard/detection-engine'

interface UploadProgressProps {
  state: UploadState
  className?: string
}

export function UploadProgress({ state, className }: UploadProgressProps) {
  return (
    <div className={cn('space-y-3', className)}>
      {/* Overall progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="font-medium">
            {state.isUploading ? 'Uploading...' : state.completedCount === state.files.length ? 'Complete' : 'Upload'}
          </span>
          <span className="text-muted-foreground">
            {state.completedCount}/{state.files.length} files ({Math.round(state.overallProgress)}%)
          </span>
        </div>
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-300',
              state.errorCount > 0 ? 'bg-accent' : 'bg-primary',
            )}
            style={{ width: `${state.overallProgress}%` }}
          />
        </div>
      </div>

      {/* Per-file status */}
      <div className="max-h-60 overflow-y-auto space-y-1">
        {state.files.map((f) => (
          <div key={f.objectName} className="flex items-center gap-2 text-xs py-1">
            {f.status === 'complete' && <CheckCircle className="w-3.5 h-3.5 text-green-600 shrink-0" />}
            {f.status === 'error' && <XCircle className="w-3.5 h-3.5 text-destructive shrink-0" />}
            {f.status === 'uploading' && <Loader2 className="w-3.5 h-3.5 text-primary animate-spin shrink-0" />}
            {f.status === 'pending' && <div className="w-3.5 h-3.5 rounded-full border border-muted-foreground shrink-0" />}
            <span className="truncate flex-1">{f.file.name}</span>
            <span className="text-muted-foreground shrink-0">{formatFileSize(f.file.size)}</span>
            {f.status === 'uploading' && (
              <span className="text-primary shrink-0">{Math.round(f.progress)}%</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
