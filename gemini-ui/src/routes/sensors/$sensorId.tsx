import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useSensors } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'

const fields: FieldDef[] = [
  { name: 'sensor_name', label: 'Name', type: 'text', required: true },
  { name: 'sensor_type_id', label: 'Sensor Type ID', type: 'text', required: true },
  { name: 'sensor_data_type_id', label: 'Data Type ID', type: 'text', required: true },
  { name: 'sensor_data_format_id', label: 'Data Format ID', type: 'text', required: true },
  { name: 'sensor_info', label: 'Info (JSON)', type: 'json' },
]

function SensorDetail() {
  const { sensorId } = Route.useParams()
  const navigate = useNavigate()
  const { data: sensor, isLoading } = useSensors.useGetById(sensorId)
  const updateMutation = useSensors.useUpdate()
  const removeMutation = useSensors.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!sensor) return <div className="p-8">Sensor not found</div>

  return (
    <div>
      <PageHeader
        title={sensor.sensor_name ?? 'Sensor'}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/sensors' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={sensor} onSubmit={(data) => updateMutation.mutate({ id: sensorId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Name</p><p>{sensor.sensor_name}</p></div>
            <div><p className="text-sm text-muted-foreground">Type ID</p><p>{sensor.sensor_type_id ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Data Type ID</p><p>{sensor.sensor_data_type_id ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Data Format ID</p><p>{sensor.sensor_data_format_id ?? '-'}</p></div>
          </div>
          {sensor.sensor_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(sensor.sensor_info, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(sensorId, { onSuccess: () => navigate({ to: '/sensors' }) })} entityName={sensor.sensor_name ?? 'Sensor'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/sensors/$sensorId')({ component: SensorDetail })
