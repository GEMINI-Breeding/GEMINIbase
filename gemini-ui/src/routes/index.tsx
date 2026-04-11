import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { PageHeader } from '@/components/layout/page-header'
import { StatCard } from '@/components/dashboard/stat-card'
import { Button } from '@/components/ui/button'
import {
  useExperiments,
  useDatasets,
  useSensors,
  useTraits,
  useGenotypes,
  usePopulations,
} from '@/hooks/use-entity-hooks'
import {
  FlaskConical,
  Database,
  Radio,
  Ruler,
  Dna,
  Users,
  Plus,
  Upload,
  FolderOpen,
} from 'lucide-react'

export const Route = createFileRoute('/')({
  component: Dashboard,
})

function Dashboard() {
  const navigate = useNavigate()
  const experiments = useExperiments.useGetAll(100, 0)
  const datasets = useDatasets.useGetAll(100, 0)
  const sensors = useSensors.useGetAll(100, 0)
  const traits = useTraits.useGetAll(100, 0)
  const genotypes = useGenotypes.useGetAll(100, 0)
  const populations = usePopulations.useGetAll(100, 0)

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Overview of your GEMINI breeding data"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Experiments"
          value={experiments.data?.length ?? 0}
          icon={FlaskConical}
          loading={experiments.isLoading}
          href="/experiments"
        />
        <StatCard
          title="Datasets"
          value={datasets.data?.length ?? 0}
          icon={Database}
          loading={datasets.isLoading}
          href="/datasets"
        />
        <StatCard
          title="Sensors"
          value={sensors.data?.length ?? 0}
          icon={Radio}
          loading={sensors.isLoading}
          href="/sensors"
        />
        <StatCard
          title="Traits"
          value={traits.data?.length ?? 0}
          icon={Ruler}
          loading={traits.isLoading}
          href="/traits"
        />
        <StatCard
          title="Genotypes"
          value={genotypes.data?.length ?? 0}
          icon={Dna}
          loading={genotypes.isLoading}
          href="/genotypes"
        />
        <StatCard
          title="Populations"
          value={populations.data?.length ?? 0}
          icon={Users}
          loading={populations.isLoading}
          href="/populations"
        />
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => navigate({ to: '/experiments' as '/' })}>
            <Plus className="h-4 w-4 mr-1" />
            New Experiment
          </Button>
          <Button variant="outline" onClick={() => navigate({ to: '/import' as '/' })}>
            <Upload className="h-4 w-4 mr-1" />
            Import Data
          </Button>
          <Button variant="outline" onClick={() => navigate({ to: '/files' as '/' })}>
            <FolderOpen className="h-4 w-4 mr-1" />
            Browse Files
          </Button>
        </div>
      </div>
    </div>
  )
}
