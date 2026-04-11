import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useVariants } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { VariantOutput } from '@/api/types'

const columns: ColumnDef<VariantOutput>[] = [
  { accessorKey: 'variant_name', header: 'Name' },
  { accessorKey: 'chromosome', header: 'Chromosome' },
  { accessorKey: 'position', header: 'Position' },
  { accessorKey: 'alleles', header: 'Alleles' },
]

const fields: FieldDef[] = [
  { name: 'variant_name', label: 'Name', type: 'text', required: true },
  { name: 'chromosome', label: 'Chromosome', type: 'number', required: true },
  { name: 'position', label: 'Position', type: 'number', required: true },
  { name: 'alleles', label: 'Alleles', type: 'text', required: true },
  { name: 'design_sequence', label: 'Design Sequence', type: 'text' },
  { name: 'variant_info', label: 'Info (JSON)', type: 'json' },
]

function VariantsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useVariants.useGetAll(50, offset)
  const createMutation = useVariants.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Variants" description="Manage genetic variants" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Variant</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/variants/$variantId', params: { variantId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Variant</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/variants/')({ component: VariantsList })
