import { useRef, useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Pencil, Trash2, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react'
import { useExperiments } from '@/hooks/use-entity-hooks'
import { experimentsApi } from '@/api/endpoints/experiments'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { DatasetFiles } from '@/components/data-viewers/dataset-files'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { EntityTable } from '@/components/crud/entity-table'
import { formatDate, cn } from '@/lib/utils'
import type { ColumnDef } from '@tanstack/react-table'
import type { SeasonOutput, SiteOutput, PopulationOutput, SensorOutput, DatasetOutput, TraitOutput, GenotypingStudyOutput } from '@/api/types'

const editFields: FieldDef[] = [
  { name: 'experiment_name', label: 'Name', type: 'text', required: true },
  { name: 'experiment_start_date', label: 'Start Date', type: 'date' },
  { name: 'experiment_end_date', label: 'End Date', type: 'date' },
  { name: 'experiment_info', label: 'Info (JSON)', type: 'json' },
]

const seasonCols: ColumnDef<SeasonOutput>[] = [
  { accessorKey: 'season_name', header: 'Name' },
  { accessorKey: 'season_start_date', header: 'Start', cell: ({ getValue }) => formatDate(getValue() as string) },
  { accessorKey: 'season_end_date', header: 'End', cell: ({ getValue }) => formatDate(getValue() as string) },
]
const siteCols: ColumnDef<SiteOutput>[] = [
  { accessorKey: 'site_name', header: 'Name' },
  { accessorKey: 'site_city', header: 'City' },
  { accessorKey: 'site_state', header: 'State' },
]
const populationCols: ColumnDef<PopulationOutput>[] = [
  { accessorKey: 'population_name', header: 'Name' },
  { accessorKey: 'population_type', header: 'Type' },
]
const sensorCols: ColumnDef<SensorOutput>[] = [
  { accessorKey: 'sensor_name', header: 'Name' },
  { accessorKey: 'sensor_type_id', header: 'Type ID' },
]
const traitCols: ColumnDef<TraitOutput>[] = [
  { accessorKey: 'trait_name', header: 'Name' },
  { accessorKey: 'trait_units', header: 'Units' },
]
const genotypeCols: ColumnDef<GenotypingStudyOutput>[] = [
  { accessorKey: 'study_name', header: 'Name' },
]

// ── Dataset card with expandable file preview ──
function DatasetCard({ dataset, experimentName }: { dataset: DatasetOutput; experimentName: string }) {
  const [expanded, setExpanded] = useState(false)
  const navigate = useNavigate()
  const info = dataset.dataset_info as Record<string, unknown> | null
  const filesPrefix = (info?.files_prefix as string) || null
  const filesList = (info?.files as string[]) || null

  return (
    <div className="rounded-lg border" data-testid="dataset-card">
      <button
        className="flex items-center gap-3 w-full text-left p-4 hover:bg-muted/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown className="w-4 h-4 shrink-0" /> : <ChevronRight className="w-4 h-4 shrink-0" />}
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{dataset.dataset_name}</p>
          <div className="flex items-center gap-2 mt-0.5">
            {dataset.collection_date && (
              <span className="text-xs text-muted-foreground">{formatDate(dataset.collection_date)}</span>
            )}
            {info?.data_type != null && (
              <Badge variant="secondary" className="text-xs">{String(info.data_type)}</Badge>
            )}
            {filesList && (
              <Badge variant="outline" className="text-xs">{filesList.length} files</Badge>
            )}
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation()
            navigate({ to: '/datasets/$datasetId', params: { datasetId: dataset.id! } })
          }}
        >
          <ExternalLink className="w-3.5 h-3.5" />
        </Button>
      </button>

      {expanded && (
        <div className="border-t p-4">
          <DatasetFiles filesPrefix={filesPrefix} />
        </div>
      )}
    </div>
  )
}

// ── All files across the entire experiment (reuses DatasetFiles with experiment prefix) ──
function ExperimentAllFiles({ experimentName }: { experimentName: string }) {
  const prefix = `gemini/Raw/${experimentName}`
  return (
    <div data-testid="experiment-files">
      <DatasetFiles filesPrefix={prefix} />
    </div>
  )
}

// ── Main component ──
function ExperimentDetail() {
  const { experimentId } = Route.useParams()
  const navigate = useNavigate()
  const { data: experiment, isLoading } = useExperiments.useGetById(experimentId)
  const queryClient = useQueryClient()
  const updateMutation = useExperiments.useUpdate()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [activeTab, setActiveTab] = useState('data')
  const deleteAbortRef = useRef<AbortController | null>(null)

  // Fetch all sub-entity lists eagerly so tab badge counts are visible immediately.
  // These are lightweight metadata queries (names + IDs only).
  const seasons = useQuery({ queryKey: ['experiments', experimentId, 'seasons'], queryFn: () => experimentsApi.getSeasons(experimentId) })
  const sites = useQuery({ queryKey: ['experiments', experimentId, 'sites'], queryFn: () => experimentsApi.getSites(experimentId) })
  const populations = useQuery({ queryKey: ['experiments', experimentId, 'populations'], queryFn: () => experimentsApi.getPopulations(experimentId) })
  const sensors = useQuery({ queryKey: ['experiments', experimentId, 'sensors'], queryFn: () => experimentsApi.getSensors(experimentId) })
  const datasets = useQuery({ queryKey: ['experiments', experimentId, 'datasets'], queryFn: () => experimentsApi.getDatasets(experimentId) })
  const traits = useQuery({ queryKey: ['experiments', experimentId, 'traits'], queryFn: () => experimentsApi.getTraits(experimentId) })
  const genotypes = useQuery({ queryKey: ['experiments', experimentId, 'genotypes'], queryFn: () => experimentsApi.getGenotypes(experimentId) })

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!experiment) return <div className="p-8">Experiment not found</div>

  return (
    <div>
      <PageHeader
        title={experiment.experiment_name}
        description={`${formatDate(experiment.experiment_start_date)} - ${formatDate(experiment.experiment_end_date)}`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/experiments' })}>
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Button>
            <Button variant="outline" onClick={() => setEditing(!editing)}>
              <Pencil className="mr-2 h-4 w-4" /> Edit
            </Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}>
              <Trash2 className="mr-2 h-4 w-4" /> Delete
            </Button>
          </div>
        }
      />

      {editing ? (
        <EntityForm
          fields={editFields}
          defaultValues={experiment}
          onSubmit={(data) =>
            updateMutation.mutate(
              { id: experimentId, data: data as never },
              { onSuccess: () => setEditing(false) },
            )
          }
          onCancel={() => setEditing(false)}
          isLoading={updateMutation.isPending}
        />
      ) : (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-2">
          <TabsList>
            <TabsTrigger value="data">Data</TabsTrigger>
            <TabsTrigger value="datasets">
              Datasets <Badge variant="secondary" className="ml-1.5" data-testid="count-datasets">{datasets.data?.length ?? 0}</Badge>
            </TabsTrigger>
            <TabsTrigger value="seasons">
              Seasons <Badge variant="secondary" className="ml-1.5" data-testid="count-seasons">{seasons.data?.length ?? 0}</Badge>
            </TabsTrigger>
            <TabsTrigger value="sites">
              Sites <Badge variant="secondary" className="ml-1.5" data-testid="count-sites">{sites.data?.length ?? 0}</Badge>
            </TabsTrigger>
            <TabsTrigger value="sensors">
              Sensors <Badge variant="secondary" className="ml-1.5" data-testid="count-sensors">{sensors.data?.length ?? 0}</Badge>
            </TabsTrigger>
            <TabsTrigger value="populations">
              Populations <Badge variant="secondary" className="ml-1.5" data-testid="count-populations">{populations.data?.length ?? 0}</Badge>
            </TabsTrigger>
            <TabsTrigger value="traits">
              Traits <Badge variant="secondary" className="ml-1.5" data-testid="count-traits">{traits.data?.length ?? 0}</Badge>
            </TabsTrigger>
            <TabsTrigger value="genotypes">
              Genotypes <Badge variant="secondary" className="ml-1.5" data-testid="count-genotypes">{genotypes.data?.length ?? 0}</Badge>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="data">
            <ExperimentAllFiles experimentName={experiment.experiment_name} />
          </TabsContent>

          <TabsContent value="datasets">
            {datasets.isLoading && <div className="py-8 text-center text-muted-foreground">Loading...</div>}
            {datasets.data && datasets.data.length === 0 && (
              <div className="py-8 text-center text-muted-foreground">No datasets associated with this experiment.</div>
            )}
            {datasets.data && datasets.data.length > 0 && (
              <div className="space-y-3">
                {datasets.data.map((ds) => (
                  <DatasetCard key={ds.id} dataset={ds} experimentName={experiment.experiment_name} />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="seasons">
            <EntityTable columns={seasonCols} data={seasons.data ?? []} isLoading={seasons.isLoading} onRowClick={(r) => navigate({ to: '/seasons/$seasonId', params: { seasonId: r.id! } })} />
          </TabsContent>
          <TabsContent value="sites">
            <EntityTable columns={siteCols} data={sites.data ?? []} isLoading={sites.isLoading} onRowClick={(r) => navigate({ to: '/sites/$siteId', params: { siteId: r.id! } })} />
          </TabsContent>
          <TabsContent value="sensors">
            <EntityTable columns={sensorCols} data={sensors.data ?? []} isLoading={sensors.isLoading} onRowClick={(r) => navigate({ to: '/sensors/$sensorId', params: { sensorId: r.id! } })} />
          </TabsContent>
          <TabsContent value="populations">
            <EntityTable columns={populationCols} data={populations.data ?? []} isLoading={populations.isLoading} onRowClick={(r) => navigate({ to: '/populations/$populationId', params: { populationId: r.id! } })} />
          </TabsContent>
          <TabsContent value="traits">
            <EntityTable columns={traitCols} data={traits.data ?? []} isLoading={traits.isLoading} onRowClick={(r) => navigate({ to: '/traits/$traitId', params: { traitId: r.id! } })} />
          </TabsContent>
          <TabsContent value="genotypes">
            <EntityTable columns={genotypeCols} data={genotypes.data ?? []} isLoading={genotypes.isLoading} onRowClick={(r) => navigate({ to: '/genotyping-studies/$studyId', params: { studyId: r.id! } })} />
          </TabsContent>
        </Tabs>
      )}

      <DeleteDialog
        open={showDelete}
        onClose={() => {
          // If a delete is in flight, abort it so Cancel actually cancels.
          // The fetch rejects with an AbortError which the catch below swallows.
          deleteAbortRef.current?.abort()
          deleteAbortRef.current = null
          setDeleting(false)
          setShowDelete(false)
        }}
        onConfirm={async () => {
          const controller = new AbortController()
          deleteAbortRef.current = controller
          setDeleting(true)
          try {
            await experimentsApi.remove(experimentId, { signal: controller.signal })
            await queryClient.invalidateQueries()
            navigate({ to: '/experiments' })
          } catch (err) {
            if (controller.signal.aborted) return
            setDeleting(false)
            alert(`Failed to delete experiment: ${err instanceof Error ? err.message : String(err)}`)
          } finally {
            if (deleteAbortRef.current === controller) deleteAbortRef.current = null
          }
        }}
        entityName={experiment.experiment_name}
        description="This will also remove any traits, populations, and datasets that are only linked to this experiment."
        isLoading={deleting}
      />
    </div>
  )
}

export const Route = createFileRoute('/experiments/$experimentId')({ component: ExperimentDetail })
