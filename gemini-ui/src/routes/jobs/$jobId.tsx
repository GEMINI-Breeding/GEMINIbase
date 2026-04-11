import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, XCircle } from 'lucide-react'
import { jobsApi } from '@/api/endpoints/jobs'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { formatDate } from '@/lib/utils'

function statusVariant(status: string) {
  switch (status) {
    case 'completed': return 'default' as const
    case 'failed': return 'destructive' as const
    case 'running': return 'secondary' as const
    default: return 'outline' as const
  }
}

function JobDetail() {
  const { jobId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: job, isLoading } = useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => jobsApi.getById(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'running' || status === 'pending' ? 3000 : false
    },
  })

  const cancelMutation = useMutation({
    mutationFn: () => jobsApi.cancel(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs', jobId] }),
  })

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!job) return <div className="p-8">Job not found</div>

  const canCancel = job.status === 'pending' || job.status === 'running'

  return (
    <div>
      <PageHeader
        title={`Job: ${job.job_type}`}
        description={`ID: ${job.id}`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/jobs' })}>
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Button>
            {canCancel && (
              <Button variant="destructive" onClick={() => cancelMutation.mutate()} disabled={cancelMutation.isPending}>
                <XCircle className="mr-2 h-4 w-4" /> Cancel Job
              </Button>
            )}
          </div>
        }
      />

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
          <div><p className="text-sm text-muted-foreground">Type</p><p>{job.job_type}</p></div>
          <div><p className="text-sm text-muted-foreground">Status</p><Badge variant={statusVariant(job.status)}>{job.status}</Badge></div>
          <div><p className="text-sm text-muted-foreground">Progress</p><p>{Math.round(job.progress * 100)}%</p></div>
          <div><p className="text-sm text-muted-foreground">Worker</p><p>{job.worker_id ?? '-'}</p></div>
          <div><p className="text-sm text-muted-foreground">Created</p><p>{formatDate(job.created_at)}</p></div>
          <div><p className="text-sm text-muted-foreground">Started</p><p>{formatDate(job.started_at)}</p></div>
          <div><p className="text-sm text-muted-foreground">Completed</p><p>{formatDate(job.completed_at)}</p></div>
          <div><p className="text-sm text-muted-foreground">Experiment ID</p><p>{job.experiment_id ?? '-'}</p></div>
        </div>

        {job.progress_detail && (
          <div className="rounded-md border p-4">
            <h3 className="text-sm font-medium mb-2">Progress Detail</h3>
            <p className="text-sm">{typeof job.progress_detail === 'string' ? job.progress_detail : JSON.stringify(job.progress_detail)}</p>
          </div>
        )}

        {job.error_message && (
          <div className="rounded-md border border-destructive p-4">
            <h3 className="text-sm font-medium mb-2 text-destructive">Error</h3>
            <p className="text-sm">{job.error_message}</p>
          </div>
        )}

        {job.parameters && (
          <div className="rounded-md border p-4">
            <h3 className="text-sm font-medium mb-2">Parameters</h3>
            <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(job.parameters, null, 2)}</pre>
          </div>
        )}

        {job.result && (
          <div className="rounded-md border p-4">
            <h3 className="text-sm font-medium mb-2">Result</h3>
            <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(job.result, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

export const Route = createFileRoute('/jobs/$jobId')({ component: JobDetail })
