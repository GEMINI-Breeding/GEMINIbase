import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useTraits } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { TraitOutput } from '@/api/types'

const columns: ColumnDef<TraitOutput>[] = [
  { accessorKey: 'trait_name', header: 'Name' },
  { accessorKey: 'trait_units', header: 'Units' },
  { accessorKey: 'trait_level_id', header: 'Level ID' },
]

const fields: FieldDef[] = [
  { name: 'trait_name', label: 'Name', type: 'text', required: true },
  { name: 'trait_units', label: 'Units', type: 'text' },
  { name: 'trait_level_id', label: 'Trait Level ID', type: 'text', required: true },
  { name: 'trait_metrics', label: 'Metrics (JSON)', type: 'json' },
  { name: 'trait_info', label: 'Info (JSON)', type: 'json' },
]

function TraitsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useTraits.useGetAll(50, offset)
  const createMutation = useTraits.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Traits" description="Manage phenotypic traits" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Trait</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/traits/$traitId', params: { traitId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Trait</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/traits/')({ component: TraitsList })
