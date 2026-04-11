import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useModels } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'

const fields: FieldDef[] = [
  { name: 'model_name', label: 'Name', type: 'text', required: true },
  { name: 'model_url', label: 'URL', type: 'text' },
  { name: 'model_info', label: 'Info (JSON)', type: 'json' },
]

function ModelDetail() {
  const { modelId } = Route.useParams()
  const navigate = useNavigate()
  const { data: model, isLoading } = useModels.useGetById(modelId)
  const updateMutation = useModels.useUpdate()
  const removeMutation = useModels.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!model) return <div className="p-8">Model not found</div>

  return (
    <div>
      <PageHeader
        title={model.model_name ?? 'Model'}
        description={model.model_url ?? undefined}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/models' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={model} onSubmit={(data) => updateMutation.mutate({ id: modelId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Name</p><p>{model.model_name}</p></div>
            <div><p className="text-sm text-muted-foreground">URL</p><p>{model.model_url ?? '-'}</p></div>
          </div>
          {model.model_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(model.model_info, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(modelId, { onSuccess: () => navigate({ to: '/models' }) })} entityName={model.model_name ?? 'Model'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/models/$modelId')({ component: ModelDetail })
