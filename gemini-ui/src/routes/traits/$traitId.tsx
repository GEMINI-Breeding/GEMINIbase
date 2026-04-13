import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useTraits } from '@/hooks/use-entity-hooks'
import { traitsApi } from '@/api/endpoints/traits'
import type { TraitRecordOutput } from '@/api/types'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'

const fields: FieldDef[] = [
  { name: 'trait_name', label: 'Name', type: 'text', required: true },
  { name: 'trait_units', label: 'Units', type: 'text' },
  { name: 'trait_level_id', label: 'Trait Level ID', type: 'text', required: true },
  { name: 'trait_metrics', label: 'Metrics (JSON)', type: 'json' },
  { name: 'trait_info', label: 'Info (JSON)', type: 'json' },
]

const PAGE_SIZE = 50

function TraitRecordsTable({ traitId }: { traitId: string }) {
  const [page, setPage] = useState(0)
  const { data: records, isLoading } = useQuery({
    queryKey: ['traitRecords', traitId, page],
    queryFn: () => traitsApi.getRecords(traitId),
  })

  if (isLoading) return <div className="animate-pulse text-sm text-muted-foreground py-4">Loading records...</div>

  const allRecords = records ?? []
  const pageRecords = allRecords.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.ceil(allRecords.length / PAGE_SIZE)

  if (allRecords.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No trait records found.</p>
  }

  const infoKeys = new Set<string>()
  for (const r of pageRecords) {
    if (r.record_info && typeof r.record_info === 'object') {
      for (const k of Object.keys(r.record_info)) {
        if (k !== 'sheet' && k !== 'source_column') infoKeys.add(k)
      }
    }
  }
  const extraKeys = [...infoKeys].sort()

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">Records</h3>
        <span className="text-xs text-muted-foreground">{allRecords.length} total records</span>
      </div>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Plot #</TableHead>
              <TableHead>Value</TableHead>
              <TableHead>Experiment</TableHead>
              <TableHead>Season</TableHead>
              <TableHead>Site</TableHead>
              <TableHead>Timestamp</TableHead>
              {extraKeys.map((k) => (
                <TableHead key={k} className="capitalize">{k}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {pageRecords.map((r, i) => (
              <TableRow key={r.id ?? i}>
                <TableCell>{r.plot_number ?? '-'}</TableCell>
                <TableCell className="font-mono">{r.trait_value ?? '-'}</TableCell>
                <TableCell>{r.experiment_name ?? '-'}</TableCell>
                <TableCell>{r.season_name ?? '-'}</TableCell>
                <TableCell>{r.site_name ?? '-'}</TableCell>
                <TableCell className="text-xs">
                  {r.timestamp ? new Date(r.timestamp).toLocaleString() : '-'}
                </TableCell>
                {extraKeys.map((k) => {
                  const info = r.record_info as Record<string, unknown> | undefined
                  const v = info?.[k]
                  return <TableCell key={k}>{v != null ? String(v) : '-'}</TableCell>
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</Button>
          <span className="text-muted-foreground">Page {page + 1} of {totalPages}</span>
          <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>Next</Button>
        </div>
      )}
    </div>
  )
}

function TraitDetail() {
  const { traitId } = Route.useParams()
  const navigate = useNavigate()
  const { data: trait, isLoading } = useTraits.useGetById(traitId)
  const updateMutation = useTraits.useUpdate()
  const removeMutation = useTraits.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!trait) return <div className="p-8">Trait not found</div>

  return (
    <div>
      <PageHeader
        title={trait.trait_name ?? 'Trait'}
        description={trait.trait_units ? `Units: ${trait.trait_units}` : undefined}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/traits' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm fields={fields} defaultValues={trait} onSubmit={(data) => updateMutation.mutate({ id: traitId, data: data as never }, { onSuccess: () => setEditing(false) })} onCancel={() => setEditing(false)} isLoading={updateMutation.isPending} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
            <div><p className="text-sm text-muted-foreground">Name</p><p>{trait.trait_name}</p></div>
            <div><p className="text-sm text-muted-foreground">Units</p><p>{trait.trait_units ?? '-'}</p></div>
            <div><p className="text-sm text-muted-foreground">Level ID</p><p>{trait.trait_level_id ?? '-'}</p></div>
          </div>
          {trait.trait_metrics && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Metrics</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(trait.trait_metrics, null, 2)}</pre>
            </div>
          )}
          {trait.trait_info && (
            <div className="rounded-md border p-4">
              <h3 className="text-sm font-medium mb-2">Info</h3>
              <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(trait.trait_info, null, 2)}</pre>
            </div>
          )}
          <div className="rounded-md border p-4">
            <TraitRecordsTable traitId={traitId} />
          </div>
        </div>
      )}
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(traitId, { onSuccess: () => navigate({ to: '/traits' }) })} entityName={trait.trait_name ?? 'Trait'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/traits/$traitId')({ component: TraitDetail })
