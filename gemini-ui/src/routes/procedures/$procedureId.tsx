import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useProcedures } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'

const fields: FieldDef[] = [
  { name: 'procedure_name', label: 'Name', type: 'text', required: true },
  { name: 'procedure_info', label: 'Info (JSON)', type: 'json' },
]

function ProcedureDetail() {
  const { procedureId } = Route.useParams()
  const navigate = useNavigate()
  const { data: procedure, isLoading } = useProcedures.useGetById(procedureId)
  const updateMutation = useProcedures.useUpdate()
  const removeMutation = useProcedures.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!procedure) return <div className="p-8">Procedure not found</div>

  return (
    <div>
      <PageHeader
        title={procedure.procedure_name ?? 'Procedure'}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/procedures' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={procedure} onSubmit={(data) => updateMutation.mutate({ id: procedureId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Name</p><p>{procedure.procedure_name}</p></div>
          </div>
          {procedure.procedure_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(procedure.procedure_info, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(procedureId, { onSuccess: () => navigate({ to: '/procedures' }) })} entityName={procedure.procedure_name ?? 'Procedure'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/procedures/$procedureId')({ component: ProcedureDetail })
