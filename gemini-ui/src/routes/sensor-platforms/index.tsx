import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useSensorPlatforms } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { SensorPlatformOutput } from '@/api/types'

const columns: ColumnDef<SensorPlatformOutput>[] = [
  { accessorKey: 'sensor_platform_name', header: 'Name' },
]

const fields: FieldDef[] = [
  { name: 'sensor_platform_name', label: 'Name', type: 'text', required: true },
  { name: 'sensor_platform_info', label: 'Info (JSON)', type: 'json' },
]

function SensorPlatformsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useSensorPlatforms.useGetAll(50, offset)
  const createMutation = useSensorPlatforms.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Sensor Platforms" description="Manage sensor platforms" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Platform</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/sensor-platforms/$sensorPlatformId', params: { sensorPlatformId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Sensor Platform</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/sensor-platforms/')({ component: SensorPlatformsList })
