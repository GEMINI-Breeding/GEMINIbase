import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { usePlots } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'

const fields: FieldDef[] = [
  { name: 'plot_number', label: 'Plot Number', type: 'number', required: true },
  { name: 'plot_row_number', label: 'Row Number', type: 'number', required: true },
  { name: 'plot_column_number', label: 'Column Number', type: 'number', required: true },
  { name: 'plot_info', label: 'Info (JSON)', type: 'json' },
  { name: 'plot_geometry_info', label: 'Geometry Info (JSON)', type: 'json' },
]

function PlotDetail() {
  const { plotId } = Route.useParams()
  const navigate = useNavigate()
  const { data: plot, isLoading } = usePlots.useGetById(plotId)
  const updateMutation = usePlots.useUpdate()
  const removeMutation = usePlots.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!plot) return <div className="p-8">Plot not found</div>

  return (
    <div>
      <PageHeader
        title={`Plot #${plot.plot_number ?? '-'}`}
        description={`Row ${plot.plot_row_number ?? '-'}, Col ${plot.plot_column_number ?? '-'}`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/plots' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={plot} onSubmit={(data) => updateMutation.mutate({ id: plotId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Plot Number</p><p>{plot.plot_number}</p></div>
            <div><p className="text-sm text-muted-foreground">Row</p><p>{plot.plot_row_number ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Column</p><p>{plot.plot_column_number ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Experiment ID</p><p>{plot.experiment_id ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Season ID</p><p>{plot.season_id ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Site ID</p><p>{plot.site_id ?? '-'}</p></div>
          </div>
          {plot.plot_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(plot.plot_info, null, 2)}</pre>
            </div>
          )}
          {plot.plot_geometry_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Geometry Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(plot.plot_geometry_info, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(plotId, { onSuccess: () => navigate({ to: '/plots' }) })} entityName={`Plot #${plot.plot_number}`} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/plots/$plotId')({ component: PlotDetail })
