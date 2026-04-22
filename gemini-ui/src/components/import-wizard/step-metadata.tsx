import { useEffect, useState } from 'react'
import type { DetectionResult } from '@/components/import-wizard/detection-engine'
import { needsSensorFields } from '@/components/import-wizard/detection-engine'
import type { ImportMetadata } from '@/components/import-wizard/wizard-shell'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { experimentsApi } from '@/api/endpoints/experiments'
import { sensorPlatformsApi } from '@/api/endpoints/sensor-platforms'
import { sensorsApi } from '@/api/endpoints/sensors'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'

const CREATE_NEW = '__create_new__'
const NOT_SELECTED = ''

interface StepMetadataProps {
  detection: DetectionResult
  /** When the user comes back to this step, restore their prior inputs. */
  initial: ImportMetadata | null
  onNext: (metadata: ImportMetadata) => void
  onBack: () => void
}

interface EntityFieldProps {
  label: string
  selectedId: string
  onSelect: (id: string) => void
  newName: string
  onNewNameChange: (value: string) => void
  options: { id: string; name: string }[]
  isLoading: boolean
  placeholder?: string
}

function EntityField({
  label,
  selectedId,
  onSelect,
  newName,
  onNewNameChange,
  options,
  isLoading,
  placeholder,
}: EntityFieldProps) {
  const testId = label.toLowerCase().replace(/ /g, '-')
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      {isLoading ? (
        <div className="flex items-center gap-2 h-10 px-3 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading...
        </div>
      ) : (
        <Select
          value={selectedId}
          onChange={(e) => onSelect(e.target.value)}
          data-testid={`select-${testId}`}
        >
          <option value={NOT_SELECTED} disabled>
            Select {label.toLowerCase()} or create new...
          </option>
          <option value={CREATE_NEW}>+ Create new...</option>
          {options.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {opt.name}
            </option>
          ))}
        </Select>
      )}
      {selectedId === CREATE_NEW && (
        <Input
          value={newName}
          onChange={(e) => onNewNameChange(e.target.value)}
          placeholder={placeholder || `New ${label.toLowerCase()} name`}
          data-testid={`new-${testId}`}
          autoFocus
        />
      )}
    </div>
  )
}

export function StepMetadata({ detection, initial, onNext, onBack }: StepMetadataProps) {
  const showSensorFields = needsSensorFields(detection.dataCategories)

  const { data: experiments, isLoading: expLoading } = useQuery({
    queryKey: ['experiments', 'all'],
    queryFn: () => experimentsApi.getAll(500, 0),
  })
  const { data: sensorPlatforms, isLoading: spLoading } = useQuery({
    queryKey: ['sensorPlatforms', 'all'],
    queryFn: () => sensorPlatformsApi.getAll(500, 0),
  })
  const { data: sensors, isLoading: sensorLoading } = useQuery({
    queryKey: ['sensors', 'all'],
    queryFn: () => sensorsApi.getAll(500, 0),
  })

  const [selectedIds, setSelectedIds] = useState(() => {
    if (!initial) {
      return { experiment: NOT_SELECTED, sensorPlatform: NOT_SELECTED, sensor: NOT_SELECTED }
    }
    return {
      experiment: initial.createNew.experiment ? CREATE_NEW : (initial.experimentId ?? NOT_SELECTED),
      // Platform/sensor are resolved by name, not id — we only know whether
      // they were newly created. For existing ones, we'll re-match to an
      // option below once the API data loads via a useEffect.
      sensorPlatform: initial.createNew.sensorPlatform ? CREATE_NEW : NOT_SELECTED,
      sensor: initial.createNew.sensor ? CREATE_NEW : NOT_SELECTED,
    }
  })

  const [newNames, setNewNames] = useState(() => {
    if (initial && initial.createNew.experiment) {
      return {
        experiment: initial.experimentName,
        sensorPlatform: initial.createNew.sensorPlatform ? initial.sensorPlatformName : detection.suggestedPlatform || '',
        sensor: initial.createNew.sensor ? initial.sensorName : detection.suggestedSensorType || '',
      }
    }
    if (initial) {
      return {
        experiment: detection.suggestedExperimentName || '',
        sensorPlatform: initial.createNew.sensorPlatform ? initial.sensorPlatformName : detection.suggestedPlatform || '',
        sensor: initial.createNew.sensor ? initial.sensorName : detection.suggestedSensorType || '',
      }
    }
    return {
      experiment: detection.suggestedExperimentName || '',
      sensorPlatform: detection.suggestedPlatform || '',
      sensor: detection.suggestedSensorType || '',
    }
  })

  const [datasetNames, setDatasetNames] = useState<string[]>(() => {
    if (initial && initial.datasetNames.length > 0) return [...initial.datasetNames]
    const today = new Date().toISOString().slice(0, 10)
    const expName = detection.suggestedExperimentName
    if (detection.fileGroups.length <= 1) {
      const date = detection.detectedDates[0] || today
      const base = expName ? `${expName} - ${date}` : `Collection ${date}`
      return [base]
    }
    return detection.fileGroups.map((g) => {
      const date = g.date || today
      return expName ? `${expName} - ${date}` : `Collection ${date}`
    })
  })

  // For existing (non-create-new) platforms and sensors we only had names
  // in `initial`; resolve those to ids once the API lists have loaded.
  useEffect(() => {
    if (!initial) return
    if (!initial.createNew.sensorPlatform && initial.sensorPlatformName && sensorPlatforms) {
      const match = sensorPlatforms.find((s) => s.sensor_platform_name === initial.sensorPlatformName)
      if (match?.id) {
        setSelectedIds((prev) => (prev.sensorPlatform === NOT_SELECTED ? { ...prev, sensorPlatform: match.id! } : prev))
      }
    }
    if (!initial.createNew.sensor && initial.sensorName && sensors) {
      const match = sensors.find((s) => s.sensor_name === initial.sensorName)
      if (match?.id) {
        setSelectedIds((prev) => (prev.sensor === NOT_SELECTED ? { ...prev, sensor: match.id! } : prev))
      }
    }
  }, [initial, sensorPlatforms, sensors])

  function select(key: keyof typeof selectedIds, value: string) {
    setSelectedIds((prev) => ({ ...prev, [key]: value }))
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

  function resolveName(
    key: keyof typeof selectedIds,
    options: { id: string; name: string }[],
  ): string {
    if (selectedIds[key] === CREATE_NEW) return newNames[key]
    return options.find((o) => o.id === selectedIds[key])?.name || ''
  }

  function isFieldOk(key: keyof typeof selectedIds): boolean {
    if (selectedIds[key] === CREATE_NEW) return newNames[key].trim() !== ''
    return selectedIds[key] !== ''
  }

  function isValid(): boolean {
    const expOk = isFieldOk('experiment')
    const datasetsOk = datasetNames.every((n) => n.trim() !== '')
    if (!showSensorFields) return expOk && datasetsOk
    const spOk = isFieldOk('sensorPlatform')
    const sensorOk = isFieldOk('sensor')
    return expOk && spOk && sensorOk && datasetsOk
  }

  const isNew = (key: keyof typeof selectedIds) => selectedIds[key] === CREATE_NEW

  function handleContinue() {
    const expOptions = (experiments || []).map((e) => ({ id: e.id || '', name: e.experiment_name }))
    const spOpts = (sensorPlatforms || []).map((s) => ({ id: s.id || '', name: s.sensor_platform_name || '' }))
    const sensorOpts = (sensors || []).map((s) => ({ id: s.id || '', name: s.sensor_name || '' }))

    const metadata: ImportMetadata = {
      experimentId: isNew('experiment') ? null : selectedIds.experiment,
      experimentName: resolveName('experiment', expOptions),
      sensorPlatformName: showSensorFields ? resolveName('sensorPlatform', spOpts) : '',
      sensorName: showSensorFields ? resolveName('sensor', sensorOpts) : '',
      datasetNames,
      createNew: {
        experiment: isNew('experiment'),
        sensorPlatform: showSensorFields ? isNew('sensorPlatform') : false,
        sensor: showSensorFields ? isNew('sensor') : false,
      },
    }
    onNext(metadata)
  }

  const expOptions = (experiments || []).map((e) => ({ id: e.id || '', name: e.experiment_name }))
  const spOptions = (sensorPlatforms || []).map((s) => ({ id: s.id || '', name: s.sensor_platform_name || '' }))
  const sensorOptions = (sensors || []).map((s) => ({ id: s.id || '', name: s.sensor_name || '' }))

  return (
    <div className="space-y-6">
      <div className="rounded-lg border p-4">
        <h3 className="font-medium mb-4">Configure Import Metadata</h3>
        <p className="text-sm text-muted-foreground mb-6">
          Confirm or edit the detected metadata. Season and site are configured
          per-sheet in the next step.
        </p>

        <div className="grid gap-5 sm:grid-cols-2">
          <EntityField
            label="Experiment"
            selectedId={selectedIds.experiment}
            onSelect={(v) => select('experiment', v)}
            newName={newNames.experiment}
            onNewNameChange={(v) => setNew('experiment', v)}
            options={expOptions}
            isLoading={expLoading}
          />

          {showSensorFields && (
            <EntityField
              label="Sensor Platform"
              selectedId={selectedIds.sensorPlatform}
              onSelect={(v) => select('sensorPlatform', v)}
              newName={newNames.sensorPlatform}
              onNewNameChange={(v) => setNew('sensorPlatform', v)}
              options={spOptions}
              isLoading={spLoading}
            />
          )}

          {showSensorFields && (
            <EntityField
              label="Sensor"
              selectedId={selectedIds.sensor}
              onSelect={(v) => select('sensor', v)}
              newName={newNames.sensor}
              onNewNameChange={(v) => setNew('sensor', v)}
              options={sensorOptions}
              isLoading={sensorLoading}
            />
          )}
        </div>
      </div>

      <div className="rounded-lg border p-4 space-y-3">
        <h3 className="font-medium">Dataset Names</h3>
        <p className="text-sm text-muted-foreground">
          A dataset groups the records from one collection event (e.g., a
          field visit on a specific day). The default combines the experiment
          and date — edit if you'd prefer something else.
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

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} data-testid="metadata-back">Back</Button>
        <Button onClick={handleContinue} disabled={!isValid()} data-testid="metadata-continue">Continue</Button>
      </div>
    </div>
  )
}
