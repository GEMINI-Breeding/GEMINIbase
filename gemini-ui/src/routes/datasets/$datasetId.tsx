import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useDatasets } from '@/hooks/use-entity-hooks'
import { datasetsApi } from '@/api/endpoints/datasets'
import { experimentsApi } from '@/api/endpoints/experiments'
import { traitsApi } from '@/api/endpoints/traits'
import { populationsApi } from '@/api/endpoints/populations'
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

async function safeList<T>(fn: () => Promise<T[]>): Promise<T[]> {
  try {
    return await fn()
  } catch {
    return []
  }
}

async function safeDelete(fn: () => Promise<void>): Promise<void> {
  try {
    await fn()
  } catch {
    // already gone or inaccessible — safe to ignore
  }
}

async function cleanupOrphans(datasetId: string) {
  const experiments = await safeList(() => datasetsApi.getExperiments(datasetId))

  // Dataset delete on the backend already cascades its MinIO prefix.
  await safeDelete(() => datasetsApi.remove(datasetId))

  // For each experiment the dataset was linked to: if no datasets remain
  // under it, delete the experiment (backend cascades its files too).
  for (const exp of experiments) {
    if (!exp.id) continue
    const remainingDatasets = await safeList(() => experimentsApi.getDatasets(exp.id!))
    if (remainingDatasets.length > 0) continue
    await safeDelete(() => experimentsApi.remove(exp.id!))
  }

  // Global orphan sweep — catches traits/populations/datasets left over from
  // partial prior deletes.
  await sweepOrphans()
}

async function sweepOrphans() {
  const [traits, populations, datasets] = await Promise.all([
    safeList(() => traitsApi.getAll(500, 0)),
    safeList(() => populationsApi.getAll(500, 0)),
    safeList(() => datasetsApi.getAll(500, 0)),
  ])

  for (const trait of traits) {
    if (!trait.id) continue
    const exps = await safeList(() => traitsApi.getExperiments(trait.id!))
    if (exps.length === 0) await safeDelete(() => traitsApi.remove(trait.id!))
  }
  for (const pop of populations) {
    if (!pop.id) continue
    const exps = await safeList(() => populationsApi.getExperiments(pop.id!))
    if (exps.length === 0) await safeDelete(() => populationsApi.remove(pop.id!))
  }
  for (const ds of datasets) {
    if (!ds.id) continue
    const exps = await safeList(() => datasetsApi.getExperiments(ds.id!))
    if (exps.length === 0) await safeDelete(() => datasetsApi.remove(ds.id!))
  }
}

function DatasetDetail() {
  const { datasetId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: dataset, isLoading } = useDatasets.useGetById(datasetId)
  const updateMutation = useDatasets.useUpdate()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!dataset) return <div className="p-8">Dataset not found</div>

  const datasetInfo = dataset.dataset_info as Record<string, unknown> | null
  const filesPrefix = (datasetInfo?.files_prefix as string) || null

  async function handleDelete() {
    setDeleting(true)
    try {
      await cleanupOrphans(datasetId)
      await queryClient.invalidateQueries()
      navigate({ to: '/datasets' })
    } catch {
      setDeleting(false)
    }
  }

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
      <DeleteDialog
        open={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        entityName={dataset.dataset_name ?? 'Dataset'}
        description="This will also remove any experiments, traits, and populations that are only linked to this dataset."
        isLoading={deleting}
      />
    </div>
  )
}

export const Route = createFileRoute('/datasets/$datasetId')({ component: DatasetDetail })
