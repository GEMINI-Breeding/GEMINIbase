import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useExperiments } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { formatDate } from '@/lib/utils'
import type { ExperimentOutput } from '@/api/types'

const columns: ColumnDef<ExperimentOutput>[] = [
  { accessorKey: 'experiment_name', header: 'Name' },
  { accessorKey: 'experiment_start_date', header: 'Start Date', cell: ({ getValue }) => formatDate(getValue() as string) },
  { accessorKey: 'experiment_end_date', header: 'End Date', cell: ({ getValue }) => formatDate(getValue() as string) },
]

const fields: FieldDef[] = [
  { name: 'experiment_name', label: 'Name', type: 'text', required: true },
  { name: 'experiment_start_date', label: 'Start Date', type: 'date' },
  { name: 'experiment_end_date', label: 'End Date', type: 'date' },
  { name: 'experiment_info', label: 'Info (JSON)', type: 'json' },
]

function ExperimentsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useExperiments.useGetAll(50, offset)
  const createMutation = useExperiments.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader
        title="Experiments"
        description="Manage breeding experiments"
        actions={
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="mr-2 h-4 w-4" /> New Experiment
          </Button>
        }
      />
      <EntityTable
        columns={columns}
        data={data ?? []}
        isLoading={isLoading}
        onRowClick={(row) => navigate({ to: '/experiments/$experimentId', params: { experimentId: row.id! } })}
        pagination={{ limit: 50, offset, onPageChange: setOffset }}
      />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader>
            <DialogTitle>Create Experiment</DialogTitle>
          </DialogHeader>
          <EntityForm
            fields={fields}
            onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })}
            onCancel={() => setShowCreate(false)}
            isLoading={createMutation.isPending}
            submitLabel="Create"
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/experiments/')({ component: ExperimentsList })
