import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useGenotypes } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { GenotypeOutput } from '@/api/types'

const columns: ColumnDef<GenotypeOutput>[] = [
  { accessorKey: 'genotype_name', header: 'Name' },
]

const fields: FieldDef[] = [
  { name: 'genotype_name', label: 'Name', type: 'text', required: true },
  { name: 'genotype_info', label: 'Info (JSON)', type: 'json' },
]

function GenotypesList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useGenotypes.useGetAll(50, offset)
  const createMutation = useGenotypes.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Genotypes" description="Manage genotype datasets" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Genotype</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/genotypes/$genotypeId', params: { genotypeId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Genotype</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/genotypes/')({ component: GenotypesList })
