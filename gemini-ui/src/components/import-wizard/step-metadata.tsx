import { useState } from 'react'
import type { DetectionResult } from '@/components/import-wizard/detection-engine'
import { needsSensorFields } from '@/components/import-wizard/detection-engine'
import type { ImportMetadata } from '@/components/import-wizard/wizard-shell'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { experimentsApi } from '@/api/endpoints/experiments'
import { seasonsApi } from '@/api/endpoints/seasons'
import { sitesApi } from '@/api/endpoints/sites'
import { sensorPlatformsApi } from '@/api/endpoints/sensor-platforms'
import { sensorsApi } from '@/api/endpoints/sensors'
import { useQuery } from '@tanstack/react-query'
import { Loader2, ToggleLeft, ToggleRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StepMetadataProps {
  detection: DetectionResult
  onNext: (metadata: ImportMetadata) => void
  onBack: () => void
}

interface EntityFieldProps {
  label: string
  isNew: boolean
  onToggle: () => void
  existingValue: string
  onExistingChange: (value: string) => void
  newValue: string
  onNewChange: (value: string) => void
  options: { id: string; name: string }[]
  isLoading: boolean
  placeholder?: string
}

function EntityField({
  label,
  isNew,
  onToggle,
  existingValue,
  onExistingChange,
  newValue,
  onNewChange,
  options,
  isLoading,
  placeholder,
}: EntityFieldProps) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">{label}</label>
        <button
          type="button"
          onClick={onToggle}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {isNew ? (
            <ToggleRight className="w-4 h-4 text-primary" />
          ) : (
            <ToggleLeft className="w-4 h-4" />
          )}
          {isNew ? 'Create new' : 'Use existing'}
        </button>
      </div>
      {isNew ? (
        <Input
          value={newValue}
          onChange={(e) => onNewChange(e.target.value)}
          placeholder={placeholder || `New ${label.toLowerCase()} name`}
          data-testid={`new-${label.toLowerCase().replace(/ /g, '-')}`}
        />
      ) : isLoading ? (
        <div className="flex items-center gap-2 h-10 px-3 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading...
        </div>
      ) : (
        <Select value={existingValue} onChange={(e) => onExistingChange(e.target.value)} data-testid={`existing-${label.toLowerCase().replace(/ /g, '-')}`}>
          <option value="">Select {label.toLowerCase()}...</option>
          {options.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {opt.name}
            </option>
          ))}
        </Select>
      )}
    </div>
  )
}

export function StepMetadata({ detection, onNext, onBack }: StepMetadataProps) {
  const showSensorFields = needsSensorFields(detection.dataCategories)

  // Fetch existing entities
  const { data: experiments, isLoading: expLoading } = useQuery({
    queryKey: ['experiments', 'all'],
    queryFn: () => experimentsApi.getAll(500, 0),
  })
  const { data: seasons, isLoading: seasonLoading } = useQuery({
    queryKey: ['seasons', 'all'],
    queryFn: () => seasonsApi.getAll(500, 0),
  })
  const { data: sites, isLoading: siteLoading } = useQuery({
    queryKey: ['sites', 'all'],
    queryFn: () => sitesApi.getAll(500, 0),
  })
  const { data: sensorPlatforms, isLoading: spLoading } = useQuery({
    queryKey: ['sensorPlatforms', 'all'],
    queryFn: () => sensorPlatformsApi.getAll(500, 0),
  })
  const { data: sensors, isLoading: sensorLoading } = useQuery({
    queryKey: ['sensors', 'all'],
    queryFn: () => sensorsApi.getAll(500, 0),
  })

  // Create new flags
  const [createNew, setCreateNew] = useState({
    experiment: !detection.suggestedExperimentName ? false : true,
    season: true,
    site: !detection.suggestedSiteName ? false : true,
    sensorPlatform: !detection.suggestedPlatform ? false : true,
    sensor: !detection.suggestedSensorType ? false : true,
  })

  // Existing entity selections (IDs)
  const [existingIds, setExistingIds] = useState({
    experiment: '',
    season: '',
    site: '',
    sensorPlatform: '',
    sensor: '',
  })

  // New entity names
  const [newNames, setNewNames] = useState({
    experiment: detection.suggestedExperimentName || '',
    season: detection.detectedDates.length > 0
      ? `Season ${detection.detectedDates[0].substring(0, 4)}`
      : '',
    site: detection.suggestedSiteName || '',
    sensorPlatform: detection.suggestedPlatform || '',
    sensor: detection.suggestedSensorType || '',
  })

  // Dataset names - one per file group or date
  const [datasetNames, setDatasetNames] = useState<string[]>(() => {
    if (detection.fileGroups.length <= 1) {
      return [detection.suggestedExperimentName || 'Dataset']
    }
    return detection.fileGroups.map((g) =>
      g.date ? `Dataset ${g.date}` : g.folder.split('/').pop() || 'Dataset',
    )
  })

  function toggle(key: keyof typeof createNew) {
    setCreateNew((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  function setExisting(key: keyof typeof existingIds, value: string) {
    setExistingIds((prev) => ({ ...prev, [key]: value }))
  }

  function setNew(key: keyof typeof newNames, value: string) {
    setNewNames((prev) => ({ ...prev, [key]: value }))
  }

  function updateDatasetName(index: number, value: string) {
    setDatasetNames((prev) => {
      const copy = [...prev]
      copy[index] = value
      return copy
    })
  }

  function getExperimentName(): string {
    if (createNew.experiment) return newNames.experiment
    const exp = experiments?.find((e) => e.id === existingIds.experiment)
    return exp?.experiment_name || ''
  }

  function isValid(): boolean {
    const expOk = createNew.experiment ? newNames.experiment.trim() !== '' : existingIds.experiment !== ''
    const seasonOk = createNew.season ? newNames.season.trim() !== '' : existingIds.season !== ''
    const siteOk = createNew.site ? newNames.site.trim() !== '' : existingIds.site !== ''
    const datasetsOk = datasetNames.every((n) => n.trim() !== '')
    if (!showSensorFields) return expOk && seasonOk && siteOk && datasetsOk
    const spOk = createNew.sensorPlatform ? newNames.sensorPlatform.trim() !== '' : existingIds.sensorPlatform !== ''
    const sensorOk = createNew.sensor ? newNames.sensor.trim() !== '' : existingIds.sensor !== ''
    return expOk && seasonOk && siteOk && spOk && sensorOk && datasetsOk
  }

  function handleContinue() {
    const metadata: ImportMetadata = {
      experimentId: createNew.experiment ? null : existingIds.experiment,
      experimentName: getExperimentName(),
      seasonName: createNew.season
        ? newNames.season
        : seasons?.find((s) => s.id === existingIds.season)?.season_name || '',
      siteName: createNew.site
        ? newNames.site
        : sites?.find((s) => s.id === existingIds.site)?.site_name || '',
      sensorPlatformName: showSensorFields
        ? (createNew.sensorPlatform
            ? newNames.sensorPlatform
            : sensorPlatforms?.find((s) => s.id === existingIds.sensorPlatform)?.sensor_platform_name || '')
        : '',
      sensorName: showSensorFields
        ? (createNew.sensor
            ? newNames.sensor
            : sensors?.find((s) => s.id === existingIds.sensor)?.sensor_name || '')
        : '',
      datasetNames,
      createNew: {
        ...createNew,
        sensorPlatform: showSensorFields ? createNew.sensorPlatform : false,
        sensor: showSensorFields ? createNew.sensor : false,
      },
    }
    onNext(metadata)
  }

  const expOptions = (experiments || []).map((e) => ({ id: e.id || '', name: e.experiment_name }))
  const seasonOptions = (seasons || []).map((s) => ({ id: s.id || '', name: s.season_name || '' }))
  const siteOptions = (sites || []).map((s) => ({ id: s.id || '', name: s.site_name || '' }))
  const spOptions = (sensorPlatforms || []).map((s) => ({ id: s.id || '', name: s.sensor_platform_name || '' }))
  const sensorOptions = (sensors || []).map((s) => ({ id: s.id || '', name: s.sensor_name || '' }))

  return (
    <div className="space-y-6">
      <div className="rounded-lg border p-4">
        <h3 className="font-medium mb-4">Configure Import Metadata</h3>
        <p className="text-sm text-muted-foreground mb-6">
          Confirm or edit the detected metadata. Fields are pre-filled based on your files.
        </p>

        <div className="grid gap-5 sm:grid-cols-2">
          <EntityField
            label="Experiment"
            isNew={createNew.experiment}
            onToggle={() => toggle('experiment')}
            existingValue={existingIds.experiment}
            onExistingChange={(v) => setExisting('experiment', v)}
            newValue={newNames.experiment}
            onNewChange={(v) => setNew('experiment', v)}
            options={expOptions}
            isLoading={expLoading}
          />

          <EntityField
            label="Season"
            isNew={createNew.season}
            onToggle={() => toggle('season')}
            existingValue={existingIds.season}
            onExistingChange={(v) => setExisting('season', v)}
            newValue={newNames.season}
            onNewChange={(v) => setNew('season', v)}
            options={seasonOptions}
            isLoading={seasonLoading}
          />

          <EntityField
            label="Site"
            isNew={createNew.site}
            onToggle={() => toggle('site')}
            existingValue={existingIds.site}
            onExistingChange={(v) => setExisting('site', v)}
            newValue={newNames.site}
            onNewChange={(v) => setNew('site', v)}
            options={siteOptions}
            isLoading={siteLoading}
          />

          {showSensorFields && (
            <EntityField
              label="Sensor Platform"
              isNew={createNew.sensorPlatform}
              onToggle={() => toggle('sensorPlatform')}
              existingValue={existingIds.sensorPlatform}
              onExistingChange={(v) => setExisting('sensorPlatform', v)}
              newValue={newNames.sensorPlatform}
              onNewChange={(v) => setNew('sensorPlatform', v)}
              options={spOptions}
              isLoading={spLoading}
            />
          )}

          {showSensorFields && (
            <EntityField
              label="Sensor"
              isNew={createNew.sensor}
              onToggle={() => toggle('sensor')}
              existingValue={existingIds.sensor}
              onExistingChange={(v) => setExisting('sensor', v)}
              newValue={newNames.sensor}
              onNewChange={(v) => setNew('sensor', v)}
              options={sensorOptions}
              isLoading={sensorLoading}
            />
          )}
        </div>
      </div>

      {/* Dataset names */}
      <div className="rounded-lg border p-4 space-y-3">
        <h3 className="font-medium">Dataset Names</h3>
        <p className="text-sm text-muted-foreground">
          One dataset will be created per file group. Edit names as needed.
        </p>
        <div className="space-y-2">
          {datasetNames.map((name, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground w-6 shrink-0">{i + 1}.</span>
              <Input
                value={name}
                onChange={(e) => updateDatasetName(i, e.target.value)}
                placeholder="Dataset name"
                data-testid={`dataset-name-${i}`}
              />
              {detection.fileGroups[i]?.date && (
                <span className="text-xs text-muted-foreground shrink-0">
                  {detection.fileGroups[i].date}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} data-testid="metadata-back">Back</Button>
        <Button onClick={handleContinue} disabled={!isValid()} data-testid="metadata-continue">Continue</Button>
      </div>
    </div>
  )
}
