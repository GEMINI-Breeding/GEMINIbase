import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useDatasets } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { DatasetFiles } from '@/components/data-viewers/dataset-files'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { formatDate } from '@/lib/utils'

const fields: FieldDef[] = [
  { name: 'dataset_name', label: 'Name', type: 'text', required: true },
  { name: 'collection_date', label: 'Collection Date', type: 'date' },
  { name: 'dataset_type_id', label: 'Dataset Type ID', type: 'text' },
  { name: 'dataset_info', label: 'Info (JSON)', type: 'json' },
]

function DatasetDetail() {
  const { datasetId } = Route.useParams()
  const navigate = useNavigate()
  const { data: dataset, isLoading } = useDatasets.useGetById(datasetId)
  const updateMutation = useDatasets.useUpdate()
  const removeMutation = useDatasets.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!dataset) return <div className="p-8">Dataset not found</div>

  // Extract files prefix from dataset_info if present
  const datasetInfo = dataset.dataset_info as Record<string, unknown> | null
  const filesPrefix = (datasetInfo?.files_prefix as string) || null

  return (
    <div>
      <PageHeader
        title={dataset.dataset_name ?? 'Dataset'}
        description={formatDate(dataset.collection_date)}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/datasets' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)} data-testid="edit-btn"><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)} data-testid="delete-btn"><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={dataset} onSubmit={(data) => updateMutation.mutate({ id: datasetId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <Tabs defaultValue="details">
          <TabsList>
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="files">Files</TabsTrigger>
          </TabsList>

          <TabsContent value="details">
            <div className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4 rounded-md border p-4" data-testid="dataset-detail">
                <div><p className="text-sm text-muted-foreground">Name</p><p>{dataset.dataset_name}</p></div>
                <div><p className="text-sm text-muted-foreground">Collection Date</p><p>{formatDate(dataset.collection_date)}</p></div>
                <div><p className="text-sm text-muted-foreground">Dataset Type ID</p><p>{dataset.dataset_type_id ?? '-'}</p></div>
              </div>
              {dataset.dataset_info && (
                <div className="rounded-md border p-4">
                  <h3 className="text-sm font-medium mb-2">Info</h3>
                  <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(dataset.dataset_info, null, 2)}</pre>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="files">
            <div className="mt-4">
              <DatasetFiles filesPrefix={filesPrefix} />
            </div>
          </TabsContent>
        </Tabs>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(datasetId, { onSuccess: () => navigate({ to: '/datasets' }) })} entityName={dataset.dataset_name ?? 'Dataset'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/datasets/$datasetId')({ component: DatasetDetail })
