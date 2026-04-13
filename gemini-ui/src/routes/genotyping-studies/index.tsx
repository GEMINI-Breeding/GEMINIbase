import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useGenotypingStudies } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { GenotypingStudyOutput } from '@/api/types'

const columns: ColumnDef<GenotypingStudyOutput>[] = [
  { accessorKey: 'study_name', header: 'Name' },
]

const fields: FieldDef[] = [
  { name: 'study_name', label: 'Name', type: 'text', required: true },
  { name: 'study_info', label: 'Info (JSON)', type: 'json' },
]

function GenotypingStudiesList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useGenotypingStudies.useGetAll(50, offset)
  const createMutation = useGenotypingStudies.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Genotyping Studies" description="Manage genotyping studies" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Study</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/genotyping-studies/$studyId', params: { studyId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Genotyping Study</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/genotyping-studies/')({ component: GenotypingStudiesList })
