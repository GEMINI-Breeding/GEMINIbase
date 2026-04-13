import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useLines } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { LineOutput } from '@/api/types'

const columns: ColumnDef<LineOutput>[] = [
  { accessorKey: 'line_name', header: 'Name' },
  { accessorKey: 'species', header: 'Species' },
]

const fields: FieldDef[] = [
  { name: 'line_name', label: 'Name', type: 'text', required: true },
  { name: 'species', label: 'Species', type: 'text' },
  { name: 'line_info', label: 'Info (JSON)', type: 'json' },
]

function LinesList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useLines.useGetAll(50, offset)
  const createMutation = useLines.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Lines" description="Manage breeding lines" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Line</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/lines/$lineId', params: { lineId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Line</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/lines/')({ component: LinesList })
