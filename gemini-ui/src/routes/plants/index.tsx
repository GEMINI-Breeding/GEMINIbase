import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { usePlants } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { PlantOutput } from '@/api/types'

const columns: ColumnDef<PlantOutput>[] = [
  { accessorKey: 'plant_number', header: 'Plant #' },
  { accessorKey: 'plot_id', header: 'Plot ID' },
  { accessorKey: 'population_id', header: 'Population ID' },
]

const fields: FieldDef[] = [
  { name: 'plant_number', label: 'Plant Number', type: 'number', required: true },
  { name: 'plant_info', label: 'Info (JSON)', type: 'json' },
]

function PlantsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = usePlants.useGetAll(50, offset)
  const createMutation = usePlants.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Plants" description="Manage individual plants" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Plant</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/plants/$plantId', params: { plantId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Plant</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/plants/')({ component: PlantsList })
