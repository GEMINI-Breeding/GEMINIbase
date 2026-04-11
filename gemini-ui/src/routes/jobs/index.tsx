import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import type { ColumnDef } from '@tanstack/react-table'
import { jobsApi } from '@/api/endpoints/jobs'
import { EntityTable } from '@/components/crud/entity-table'
import { PageHeader } from '@/components/layout/page-header'
import { Badge } from '@/components/ui/badge'
import type { JobOutput } from '@/api/types'

function statusVariant(status: string) {
  switch (status) {
    case 'completed': return 'default' as const
    case 'failed': return 'destructive' as const
    case 'running': return 'secondary' as const
    default: return 'outline' as const
  }
}

const columns: ColumnDef<JobOutput>[] = [
  { accessorKey: 'job_type', header: 'Type' },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ getValue }) => {
      const status = getValue() as string
      return <Badge variant={statusVariant(status)}>{status}</Badge>
    },
  },
  {
    accessorKey: 'progress',
    header: 'Progress',
    cell: ({ getValue }) => `${Math.round((getValue() as number) * 100)}%`,
  },
  { accessorKey: 'created_at', header: 'Created' },
]

function JobsList() {
  const [offset, setOffset] = useState(0)
  const { data, isLoading } = useQuery({
    queryKey: ['jobs', offset],
    queryFn: () => jobsApi.getAll({ limit: 50, offset }),
  })
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Jobs" description="View background jobs and their status" />
      <EntityTable
        columns={columns}
        data={data ?? []}
        isLoading={isLoading}
        onRowClick={(row) => navigate({ to: '/jobs/$jobId', params: { jobId: row.id! } })}
        pagination={{ limit: 50, offset, onPageChange: setOffset }}
      />
    </div>
  )
}

export const Route = createFileRoute('/jobs/')({ component: JobsList })
