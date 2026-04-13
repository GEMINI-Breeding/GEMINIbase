import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useAccessions } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { AccessionOutput } from '@/api/types'

const columns: ColumnDef<AccessionOutput>[] = [
  { accessorKey: 'accession_name', header: 'Name' },
  { accessorKey: 'species', header: 'Species' },
]

const fields: FieldDef[] = [
  { name: 'accession_name', label: 'Name', type: 'text', required: true },
  { name: 'species', label: 'Species', type: 'text' },
  { name: 'line_name', label: 'Line Name', type: 'text' },
  { name: 'population_name', label: 'Population Name', type: 'text' },
  { name: 'accession_info', label: 'Info (JSON)', type: 'json' },
]

function AccessionsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useAccessions.useGetAll(50, offset)
  const createMutation = useAccessions.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Accessions" description="Manage accessions" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Accession</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/accessions/$accessionId', params: { accessionId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Accession</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/accessions/')({ component: AccessionsList })
