import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useVariants } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'

const fields: FieldDef[] = [
  { name: 'variant_name', label: 'Name', type: 'text', required: true },
  { name: 'chromosome', label: 'Chromosome', type: 'number', required: true },
  { name: 'position', label: 'Position', type: 'number', required: true },
  { name: 'alleles', label: 'Alleles', type: 'text', required: true },
  { name: 'design_sequence', label: 'Design Sequence', type: 'text' },
  { name: 'variant_info', label: 'Info (JSON)', type: 'json' },
]

function VariantDetail() {
  const { variantId } = Route.useParams()
  const navigate = useNavigate()
  const { data: variant, isLoading } = useVariants.useGetById(variantId)
  const updateMutation = useVariants.useUpdate()
  const removeMutation = useVariants.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!variant) return <div className="p-8">Variant not found</div>

  return (
    <div>
      <PageHeader
        title={variant.variant_name ?? 'Variant'}
        description={`Chr ${variant.chromosome ?? '-'} : ${variant.position ?? '-'}`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/variants' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={variant} onSubmit={(data) => updateMutation.mutate({ id: variantId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Name</p><p>{variant.variant_name}</p></div>
            <div><p className="text-sm text-muted-foreground">Chromosome</p><p>{variant.chromosome ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Position</p><p>{variant.position ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Alleles</p><p>{variant.alleles ?? '-'}</p></div>
            <div className="col-span-2"><p className="text-sm text-muted-foreground">Design Sequence</p><p className="font-mono text-sm break-all">{variant.design_sequence ?? '-'}</p></div>
          </div>
          {variant.variant_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(variant.variant_info, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(variantId, { onSuccess: () => navigate({ to: '/variants' }) })} entityName={variant.variant_name ?? 'Variant'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/variants/$variantId')({ component: VariantDetail })
