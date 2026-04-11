import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useSeasons } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/lib/utils'

const fields: FieldDef[] = [
  { name: 'season_name', label: 'Name', type: 'text', required: true },
  { name: 'season_start_date', label: 'Start Date', type: 'date' },
  { name: 'season_end_date', label: 'End Date', type: 'date' },
  { name: 'season_info', label: 'Info (JSON)', type: 'json' },
]

function SeasonDetail() {
  const { seasonId } = Route.useParams()
  const navigate = useNavigate()
  const { data: season, isLoading } = useSeasons.useGetById(seasonId)
  const updateMutation = useSeasons.useUpdate()
  const removeMutation = useSeasons.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!season) return <div className="p-8">Season not found</div>

  return (
    <div>
      <PageHeader
        title={season.season_name ?? 'Season'}
        description={`${formatDate(season.season_start_date)} - ${formatDate(season.season_end_date)}`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/seasons' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={season} onSubmit={(data) => updateMutation.mutate({ id: seasonId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Name</p><p>{season.season_name}</p></div>
            <div><p className="text-sm text-muted-foreground">Experiment ID</p><p>{season.experiment_id ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Start Date</p><p>{formatDate(season.season_start_date)}</p></div>
            <div><p className="text-sm text-muted-foreground">End Date</p><p>{formatDate(season.season_end_date)}</p></div>
          </div>
          {season.season_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(season.season_info, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(seasonId, { onSuccess: () => navigate({ to: '/seasons' }) })} entityName={season.season_name ?? 'Season'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/seasons/$seasonId')({ component: SeasonDetail })
