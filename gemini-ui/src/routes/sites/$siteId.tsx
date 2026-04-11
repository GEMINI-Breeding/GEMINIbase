import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useSites } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'

const fields: FieldDef[] = [
  { name: 'site_name', label: 'Name', type: 'text', required: true },
  { name: 'site_city', label: 'City', type: 'text' },
  { name: 'site_state', label: 'State', type: 'text' },
  { name: 'site_country', label: 'Country', type: 'text' },
  { name: 'site_info', label: 'Info (JSON)', type: 'json' },
]

function SiteDetail() {
  const { siteId } = Route.useParams()
  const navigate = useNavigate()
  const { data: site, isLoading } = useSites.useGetById(siteId)
  const updateMutation = useSites.useUpdate()
  const removeMutation = useSites.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!site) return <div className="p-8">Site not found</div>

  return (
    <div>
      <PageHeader
        title={site.site_name ?? 'Site'}
        description={[site.site_city, site.site_state, site.site_country].filter(Boolean).join(', ') || undefined}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/sites' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={site} onSubmit={(data) => updateMutation.mutate({ id: siteId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Name</p><p>{site.site_name}</p></div>
            <div><p className="text-sm text-muted-foreground">City</p><p>{site.site_city ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">State</p><p>{site.site_state ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Country</p><p>{site.site_country ?? '-'}</p></div>
          </div>
          {site.site_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(site.site_info, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(siteId, { onSuccess: () => navigate({ to: '/sites' }) })} entityName={site.site_name ?? 'Site'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/sites/$siteId')({ component: SiteDetail })
