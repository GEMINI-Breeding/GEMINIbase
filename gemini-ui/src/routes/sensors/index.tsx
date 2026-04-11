import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useSensors } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { SensorOutput } from '@/api/types'

const columns: ColumnDef<SensorOutput>[] = [
  { accessorKey: 'sensor_name', header: 'Name' },
  { accessorKey: 'sensor_type_id', header: 'Type ID' },
  { accessorKey: 'sensor_data_type_id', header: 'Data Type ID' },
]

const fields: FieldDef[] = [
  { name: 'sensor_name', label: 'Name', type: 'text', required: true },
  { name: 'sensor_type_id', label: 'Sensor Type ID', type: 'text', required: true },
  { name: 'sensor_data_type_id', label: 'Data Type ID', type: 'text', required: true },
  { name: 'sensor_data_format_id', label: 'Data Format ID', type: 'text', required: true },
  { name: 'sensor_info', label: 'Info (JSON)', type: 'json' },
]

function SensorsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useSensors.useGetAll(50, offset)
  const createMutation = useSensors.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Sensors" description="Manage sensors" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Sensor</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/sensors/$sensorId', params: { sensorId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Sensor</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/sensors/')({ component: SensorsList })
