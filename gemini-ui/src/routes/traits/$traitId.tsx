import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useTraits } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'

const fields: FieldDef[] = [
  { name: 'trait_name', label: 'Name', type: 'text', required: true },
  { name: 'trait_units', label: 'Units', type: 'text' },
  { name: 'trait_level_id', label: 'Trait Level ID', type: 'text', required: true },
  { name: 'trait_metrics', label: 'Metrics (JSON)', type: 'json' },
  { name: 'trait_info', label: 'Info (JSON)', type: 'json' },
]

function TraitDetail() {
  const { traitId } = Route.useParams()
  const navigate = useNavigate()
  const { data: trait, isLoading } = useTraits.useGetById(traitId)
  const updateMutation = useTraits.useUpdate()
  const removeMutation = useTraits.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!trait) return <div className="p-8">Trait not found</div>

  return (
    <div>
      <PageHeader
        title={trait.trait_name ?? 'Trait'}
        description={trait.trait_units ? `Units: ${trait.trait_units}` : undefined}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/traits' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={trait} onSubmit={(data) => updateMutation.mutate({ id: traitId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Name</p><p>{trait.trait_name}</p></div>
            <div><p className="text-sm text-muted-foreground">Units</p><p>{trait.trait_units ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Level ID</p><p>{trait.trait_level_id ?? '-'}</p></div>
          </div>
          {trait.trait_metrics && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Metrics</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(trait.trait_metrics, null, 2)}</pre>
            </div>
          )}
          {trait.trait_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(trait.trait_info, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(traitId, { onSuccess: () => navigate({ to: '/traits' }) })} entityName={trait.trait_name ?? 'Trait'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/traits/$traitId')({ component: TraitDetail })
