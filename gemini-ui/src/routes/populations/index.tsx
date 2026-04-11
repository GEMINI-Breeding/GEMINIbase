import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { usePopulations } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { PopulationOutput } from '@/api/types'

const columns: ColumnDef<PopulationOutput>[] = [
  { accessorKey: 'population_name', header: 'Name' },
  { accessorKey: 'population_accession', header: 'Accession' },
]

const fields: FieldDef[] = [
  { name: 'population_name', label: 'Name', type: 'text', required: true },
  { name: 'population_accession', label: 'Accession', type: 'text' },
  { name: 'population_info', label: 'Info (JSON)', type: 'json' },
]

function PopulationsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = usePopulations.useGetAll(50, offset)
  const createMutation = usePopulations.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Populations" description="Manage breeding populations" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Population</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/populations/$populationId', params: { populationId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Population</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/populations/')({ component: PopulationsList })
