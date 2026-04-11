import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { usePlants } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'

const fields: FieldDef[] = [
  { name: 'plant_number', label: 'Plant Number', type: 'number', required: true },
  { name: 'plant_info', label: 'Info (JSON)', type: 'json' },
]

function PlantDetail() {
  const { plantId } = Route.useParams()
  const navigate = useNavigate()
  const { data: plant, isLoading } = usePlants.useGetById(plantId)
  const updateMutation = usePlants.useUpdate()
  const removeMutation = usePlants.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!plant) return <div className="p-8">Plant not found</div>

  return (
    <div>
      <PageHeader
        title={`Plant #${plant.plant_number}`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/plants' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={plant} onSubmit={(data) => updateMutation.mutate({ id: plantId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Plant Number</p><p>{plant.plant_number}</p></div>
            <div><p className="text-sm text-muted-foreground">Plot ID</p><p>{plant.plot_id ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Population ID</p><p>{plant.population_id ?? '-'}</p></div>
          </div>
          {plant.plant_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(plant.plant_info, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(plantId, { onSuccess: () => navigate({ to: '/plants' }) })} entityName={`Plant #${plant.plant_number}`} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/plants/$plantId')({ component: PlantDetail })
