import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { usePlots } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { PlotOutput } from '@/api/types'

const columns: ColumnDef<PlotOutput>[] = [
  { accessorKey: 'plot_number', header: 'Plot #' },
  { accessorKey: 'plot_row_number', header: 'Row' },
  { accessorKey: 'plot_column_number', header: 'Column' },
  { accessorKey: 'experiment_id', header: 'Experiment ID' },
]

const fields: FieldDef[] = [
  { name: 'plot_number', label: 'Plot Number', type: 'number', required: true },
  { name: 'plot_row_number', label: 'Row Number', type: 'number', required: true },
  { name: 'plot_column_number', label: 'Column Number', type: 'number', required: true },
  { name: 'plot_info', label: 'Info (JSON)', type: 'json' },
  { name: 'plot_geometry_info', label: 'Geometry Info (JSON)', type: 'json' },
]

function PlotsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = usePlots.useGetAll(50, offset)
  const createMutation = usePlots.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Plots" description="Manage field plots" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Plot</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/plots/$plotId', params: { plotId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Plot</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/plots/')({ component: PlotsList })
