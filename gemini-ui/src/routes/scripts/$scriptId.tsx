import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useScripts } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'

const fields: FieldDef[] = [
  { name: 'script_name', label: 'Name', type: 'text', required: true },
  { name: 'script_url', label: 'URL', type: 'text' },
  { name: 'script_extension', label: 'Extension', type: 'text' },
  { name: 'script_info', label: 'Info (JSON)', type: 'json' },
]

function ScriptDetail() {
  const { scriptId } = Route.useParams()
  const navigate = useNavigate()
  const { data: script, isLoading } = useScripts.useGetById(scriptId)
  const updateMutation = useScripts.useUpdate()
  const removeMutation = useScripts.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!script) return <div className="p-8">Script not found</div>

  return (
    <div>
      <PageHeader
        title={script.script_name ?? 'Script'}
        description={script.script_extension ? `Extension: ${script.script_extension}` : undefined}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/scripts' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={script} onSubmit={(data) => updateMutation.mutate({ id: scriptId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Name</p><p>{script.script_name}</p></div>
            <div><p className="text-sm text-muted-foreground">URL</p><p>{script.script_url ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Extension</p><p>{script.script_extension ?? '-'}</p></div>
          </div>
          {script.script_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(script.script_info, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(scriptId, { onSuccess: () => navigate({ to: '/scripts' }) })} entityName={script.script_name ?? 'Script'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/scripts/$scriptId')({ component: ScriptDetail })
