import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useSeasons } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { formatDate } from '@/lib/utils'
import type { SeasonOutput } from '@/api/types'

const columns: ColumnDef<SeasonOutput>[] = [
  { accessorKey: 'season_name', header: 'Name' },
  { accessorKey: 'season_start_date', header: 'Start Date', cell: ({ getValue }) => formatDate(getValue() as string) },
  { accessorKey: 'season_end_date', header: 'End Date', cell: ({ getValue }) => formatDate(getValue() as string) },
  { accessorKey: 'experiment_id', header: 'Experiment ID' },
]

const fields: FieldDef[] = [
  { name: 'season_name', label: 'Name', type: 'text', required: true },
  { name: 'season_start_date', label: 'Start Date', type: 'date' },
  { name: 'season_end_date', label: 'End Date', type: 'date' },
  { name: 'season_info', label: 'Info (JSON)', type: 'json' },
]

function SeasonsList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useSeasons.useGetAll(50, offset)
  const createMutation = useSeasons.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader
        title="Seasons"
        description="Manage growing seasons"
        actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Season</Button>}
      />
      <EntityTable
        columns={columns}
        data={data ?? []}
        isLoading={isLoading}
        onRowClick={(row) => navigate({ to: '/seasons/$seasonId', params: { seasonId: row.id! } })}
        pagination={{ limit: 50, offset, onPageChange: setOffset }}
      />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Season</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/seasons/')({ component: SeasonsList })
