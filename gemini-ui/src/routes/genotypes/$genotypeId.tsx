import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useGenotypes } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'

const fields: FieldDef[] = [
  { name: 'genotype_name', label: 'Name', type: 'text', required: true },
  { name: 'genotype_info', label: 'Info (JSON)', type: 'json' },
]

function GenotypeDetail() {
  const { genotypeId } = Route.useParams()
  const navigate = useNavigate()
  const { data: genotype, isLoading } = useGenotypes.useGetById(genotypeId)
  const updateMutation = useGenotypes.useUpdate()
  const removeMutation = useGenotypes.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!genotype) return <div className="p-8">Genotype not found</div>

  return (
    <div>
      <PageHeader
        title={genotype.genotype_name ?? 'Genotype'}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/genotypes' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={genotype} onSubmit={(data) => updateMutation.mutate({ id: genotypeId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Name</p><p>{genotype.genotype_name}</p></div>
          </div>
          {genotype.genotype_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(genotype.genotype_info, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(genotypeId, { onSuccess: () => navigate({ to: '/genotypes' }) })} entityName={genotype.genotype_name ?? 'Genotype'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/genotypes/$genotypeId')({ component: GenotypeDetail })
