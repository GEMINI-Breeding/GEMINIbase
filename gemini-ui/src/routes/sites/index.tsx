import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { useSites } from '@/hooks/use-entity-hooks'
import { EntityTable } from '@/components/crud/entity-table'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { SiteOutput } from '@/api/types'

const columns: ColumnDef<SiteOutput>[] = [
  { accessorKey: 'site_name', header: 'Name' },
  { accessorKey: 'site_city', header: 'City' },
  { accessorKey: 'site_state', header: 'State' },
  { accessorKey: 'site_country', header: 'Country' },
]

const fields: FieldDef[] = [
  { name: 'site_name', label: 'Name', type: 'text', required: true },
  { name: 'site_city', label: 'City', type: 'text' },
  { name: 'site_state', label: 'State', type: 'text' },
  { name: 'site_country', label: 'Country', type: 'text' },
  { name: 'site_info', label: 'Info (JSON)', type: 'json' },
]

function SitesList() {
  const [offset, setOffset] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useSites.useGetAll(50, offset)
  const createMutation = useSites.useCreate()
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Sites" description="Manage field sites" actions={<Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" /> New Site</Button>} />
      <EntityTable columns={columns} data={data ?? []} isLoading={isLoading} onRowClick={(row) => navigate({ to: '/sites/$siteId', params: { siteId: row.id! } })} pagination={{ limit: 50, offset, onPageChange: setOffset }} />
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader><DialogTitle>Create Site</DialogTitle></DialogHeader>
          <EntityForm fields={fields} onSubmit={(data) => createMutation.mutate(data as never, { onSuccess: () => setShowCreate(false) })} onCancel={() => setShowCreate(false)} isLoading={createMutation.isPending} submitLabel="Create" />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute('/sites/')({ component: SitesList })
