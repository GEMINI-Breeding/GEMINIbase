import { useState, useEffect } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Trash2 } from 'lucide-react'
import { useTraits } from '@/hooks/use-entity-hooks'
import { traitsApi } from '@/api/endpoints/traits'
import type { TraitRecordOutput } from '@/api/types'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { TraitCharts } from '@/components/data-viewers/trait-charts'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'

const PAGE_SIZE = 50

function InlineField({
  label,
  value,
  placeholder,
  onSave,
}: {
  label: string
  value: string | null | undefined
  placeholder?: string
  onSave: (value: string) => void
}) {
  const [draft, setDraft] = useState(value ?? '')

  // Keep local state in sync if the value changes from elsewhere (e.g. after save).
  useEffect(() => {
    setDraft(value ?? '')
  }, [value])

  function commit() {
    const trimmed = draft.trim()
    if (trimmed !== (value ?? '').trim()) {
      onSave(trimmed)
    }
  }

  return (
    <div className="space-y-1">
      <p className="text-sm text-muted-foreground">{label}</p>
      <Input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.currentTarget.blur()
          } else if (e.key === 'Escape') {
            setDraft(value ?? '')
            e.currentTarget.blur()
          }
        }}
        placeholder={placeholder}
        className="border-transparent hover:border-input focus:border-input"
      />
    </div>
  )
}

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
  const queryClient = useQueryClient()
  const { data: trait, isLoading } = useTraits.useGetById(traitId)
  const updateMutation = useTraits.useUpdate()
  const removeMutation = useTraits.useRemove()
  const [showDelete, setShowDelete] = useState(false)

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!trait) return <div className="p-8">Trait not found</div>

  function saveField(field: 'trait_name' | 'trait_units', value: string) {
    updateMutation.mutate(
      {
        id: traitId,
        data: { [field]: value || undefined } as never,
      },
      {
        // Renaming the trait propagates the new name into the
        // denormalized `trait_records.trait_name` column (see
        // Trait.update → cascade_rename on the backend). React-query's
        // records cache under ['traitRecords', ...] is keyed per-trait
        // and is NOT covered by the generic ['traits'] invalidation in
        // useUpdate, so it would keep serving the old (empty, for name
        // searches) response. Force-invalidate it here so Records and
        // Visualize refetch and reflect the renamed trait immediately.
        onSuccess: () => {
          if (field === 'trait_name') {
            queryClient.invalidateQueries({ queryKey: ['traitRecords', traitId] })
          }
        },
      },
    )
  }

  return (
    <div>
      <PageHeader
        title={trait.trait_name ?? 'Trait'}
        description={trait.trait_units ? `Units: ${trait.trait_units}` : undefined}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/traits' })}><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      <Tabs defaultValue="details" className="mt-2">
        <TabsList>
          <TabsTrigger value="details">Details</TabsTrigger>
          <TabsTrigger value="records">Records</TabsTrigger>
          <TabsTrigger value="visualize">Visualize</TabsTrigger>
        </TabsList>

        <TabsContent value="details">
          <div className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
              <InlineField
                label="Name"
                value={trait.trait_name}
                placeholder="Trait name"
                onSave={(v) => saveField('trait_name', v)}
              />
              <InlineField
                label="Units"
                value={trait.trait_units}
                placeholder="e.g. cm, count, g/m²"
                onSave={(v) => saveField('trait_units', v)}
              />
              <div>
                <p className="text-sm text-muted-foreground">Level ID</p>
                <p className="h-10 flex items-center">{trait.trait_level_id ?? '-'}</p>
              </div>
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
          </div>
        </TabsContent>

          <TabsContent value="records">
            <div className="mt-4 rounded-md border p-4">
              <TraitRecordsTable traitId={traitId} />
            </div>
          </TabsContent>

          <TabsContent value="visualize">
            <div className="mt-4 rounded-md border p-4">
              <TraitCharts
                traitId={traitId}
                traitName={trait.trait_name ?? 'Trait'}
                traitUnits={trait.trait_units ?? undefined}
              />
            </div>
          </TabsContent>
      </Tabs>
      <DeleteDialog open={showDelete} onClose={() => setShowDelete(false)} onConfirm={() => removeMutation.mutate(traitId, { onSuccess: () => navigate({ to: '/traits' }) })} entityName={trait.trait_name ?? 'Trait'} isLoading={removeMutation.isPending} />
    </div>
  )
}

export const Route = createFileRoute('/traits/$traitId')({ component: TraitDetail })
