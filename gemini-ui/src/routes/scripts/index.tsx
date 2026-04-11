import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useScripts } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { ScriptOutput } from '@/api/types'

const columns: ColumnDef<ScriptOutput>[] = [
  { accessorKey: 'script_name', header: 'Name' },
  { accessorKey: 'script_url', header: 'URL' },
  { accessorKey: 'script_extension', header: 'Extension' },
]

const fields: FieldDef[] = [
  { name: 'script_name', label: 'Name', type: 'text', required: true },
  { name: 'script_url', label: 'URL', type: 'text' },
  { name: 'script_extension', label: 'Extension', type: 'text' },
  { name: 'script_info', label: 'Info (JSON)', type: 'json' },
]

function ScriptsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useScripts.useGetAll(50, offset)
  const createMutation = useScripts.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Scripts" description="Manage analysis scripts" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Script</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/scripts/$scriptId', params: { scriptId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Script</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/scripts/')({ component: ScriptsList })
