import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useModels } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { ModelOutput } from '@/api/types'

const columns: ColumnDef<ModelOutput>[] = [
  { accessorKey: 'model_name', header: 'Name' },
  { accessorKey: 'model_url', header: 'URL' },
]

const fields: FieldDef[] = [
  { name: 'model_name', label: 'Name', type: 'text', required: true },
  { name: 'model_url', label: 'URL', type: 'text' },
  { name: 'model_info', label: 'Info (JSON)', type: 'json' },
]

function ModelsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useModels.useGetAll(50, offset)
  const createMutation = useModels.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Models" description="Manage ML models" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Model</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/models/$modelId', params: { modelId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Model</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/models/')({ component: ModelsList })
