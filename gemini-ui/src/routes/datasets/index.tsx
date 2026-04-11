import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useDatasets } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { formatDate } from '@/lib/utils'
import type { DatasetOutput } from '@/api/types'

const columns: ColumnDef<DatasetOutput>[] = [
  { accessorKey: 'dataset_name', header: 'Name' },
  { accessorKey: 'collection_date', header: 'Collection Date', cell: ({ getValue }) => formatDate(getValue() as string) },
  { accessorKey: 'dataset_type_id', header: 'Type ID' },
]

const fields: FieldDef[] = [
  { name: 'dataset_name', label: 'Name', type: 'text', required: true },
  { name: 'collection_date', label: 'Collection Date', type: 'date' },
  { name: 'dataset_type_id', label: 'Dataset Type ID', type: 'text' },
  { name: 'dataset_info', label: 'Info (JSON)', type: 'json' },
]

function DatasetsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useDatasets.useGetAll(50, offset)
  const createMutation = useDatasets.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Datasets" description="Manage data collections" actions={<Button onClick={() => setShowCreate(true)} data-testid="new-dataset-btn"><Plus className="mr-2 h-4 w-4" /> New Dataset</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/datasets/$datasetId', params: { datasetId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Dataset</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/datasets/')({ component: DatasetsList })
