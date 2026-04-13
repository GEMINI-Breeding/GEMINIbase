import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useAccessions } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'

const fields: FieldDef[] = [
  { name: 'accession_name', label: 'Name', type: 'text', required: true },
  { name: 'species', label: 'Species', type: 'text' },
  { name: 'accession_info', label: 'Info (JSON)', type: 'json' },
]

function AccessionDetail() {
  const { accessionId } = Route.useParams()
  const navigate = useNavigate()
  const { data: accession, isLoading } = useAccessions.useGetById(accessionId)
  const updateMutation = useAccessions.useUpdate()
  const removeMutation = useAccessions.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!accession) return <div className="p-8">Accession not found</div>

  return (
    <div>
      <PageHeader
        title={accession.accession_name ?? 'Accession'}
        description={accession.species ?? undefined}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/accessions' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={accession} onSubmit={(data) => updateMutation.mutate({ id: accessionId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Name</p><p>{accession.accession_name}</p></div>
            <div><p className="text-sm text-muted-foreground">Species</p><p>{accession.species ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Line ID</p><p>{accession.line_id ?? '-'}</p></div>
          </div>
          {accession.accession_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(accession.accession_info, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(accessionId, { onSuccess: () => navigate({ to: '/accessions' }) })} entityName={accession.accession_name ?? 'Accession'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/accessions/$accessionId')({ component: AccessionDetail })
