import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { DetectionResult } from '@/components/import-wizard/detection-engine'
import type { GenomicMetadata } from '@/components/import-wizard/genomic/genomic-wizard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { genotypingStudiesApi } from '@/api/endpoints/genotyping-studies'
import { experimentsApi } from '@/api/endpoints/experiments'
import { Loader2 } from 'lucide-react'

const CREATE_NEW = '__create_new__'
const NOT_SELECTED = ''
const NO_EXPERIMENT = '__none__'

interface StepMetadataGenomicProps {
  detection: DetectionResult
  initial: GenomicMetadata | null
  onNext: (metadata: GenomicMetadata) => void
  onBack: () => void
}

export function StepMetadataGenomic({
  detection,
  initial,
  onNext,
  onBack,
}: StepMetadataGenomicProps) {
  const [studySelection, setStudySelection] = useState<string>(
    initial ? (initial.studyId ?? (initial.createNewStudy ? CREATE_NEW : NOT_SELECTED)) : NOT_SELECTED,
  )
  const [newStudyName, setNewStudyName] = useState<string>(
    initial?.createNewStudy ? initial.studyName : '',
  )
  const [experimentSelection, setExperimentSelection] = useState<string>(
    initial?.experimentName ?? NO_EXPERIMENT,
  )

  const { data: studies, isLoading: studiesLoading } = useQuery({
    queryKey: ['genotyping-studies'],
    queryFn: () => genotypingStudiesApi.getAll(200),
  })
  const { data: experiments, isLoading: expsLoading } = useQuery({
    queryKey: ['experiments'],
    queryFn: () => experimentsApi.getAll(200),
  })

  const shape = detection.genomicShape
  const sampleCount = shape?.sampleHeaders.length ?? 0

  useEffect(() => {
    // If the user hasn't named a new study, suggest one from the file.
    if (studySelection === CREATE_NEW && !newStudyName) {
      const f = detection.genomicFile
      if (f) {
        const base = f.name.replace(/\.[^.]+$/, '')
        setNewStudyName(base)
      }
    }
  }, [studySelection, newStudyName, detection.genomicFile])

  const canContinue = (() => {
    if (studySelection === NOT_SELECTED) return false
    if (studySelection === CREATE_NEW && !newStudyName.trim()) return false
    return true
  })()

  function handleContinue() {
    if (!canContinue) return
    if (studySelection === CREATE_NEW) {
      onNext({
        studyId: null,
        studyName: newStudyName.trim(),
        createNewStudy: true,
        experimentName: experimentSelection === NO_EXPERIMENT ? null : experimentSelection,
      })
    } else {
      const match = studies?.find((s) => s.id === studySelection)
      if (!match?.study_name) return
      onNext({
        studyId: match.id ?? null,
        studyName: match.study_name,
        createNewStudy: false,
        experimentName: experimentSelection === NO_EXPERIMENT ? null : experimentSelection,
      })
    }
  }

  return (
    <div className="space-y-6">
      {shape && (
        <div className="rounded-lg border p-4 space-y-2 text-sm" data-testid="genomic-file-summary">
          <div className="flex items-center justify-between">
            <span className="font-medium">File shape</span>
            <span className="text-muted-foreground uppercase text-xs tracking-wide">
              {shape.format}
            </span>
          </div>
          <div className="text-muted-foreground">
            {sampleCount.toLocaleString()} sample column{sampleCount === 1 ? '' : 's'} detected
            {shape.variantNameColumnIndex !== null && (
              <> · variant column identified</>
            )}
          </div>
        </div>
      )}

      <div className="space-y-1.5">
        <label className="text-sm font-medium">Genotyping Study</label>
        {studiesLoading ? (
          <div className="flex items-center gap-2 h-10 px-3 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading...
          </div>
        ) : (
          <Select
            value={studySelection}
            onChange={(e) => setStudySelection(e.target.value)}
            data-testid="select-study"
          >
            <option value={NOT_SELECTED} disabled>
              Select an existing study or create a new one...
            </option>
            <option value={CREATE_NEW}>+ Create new study...</option>
            {(studies ?? []).map((s) => (
              <option key={s.id} value={s.id}>{s.study_name}</option>
            ))}
          </Select>
        )}
        {studySelection === CREATE_NEW && (
          <Input
            value={newStudyName}
            onChange={(e) => setNewStudyName(e.target.value)}
            placeholder="New study name (e.g. cowpea-magic-snp)"
            data-testid="new-study-name"
            autoFocus
          />
        )}
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium">Linked Experiment (optional)</label>
        {expsLoading ? (
          <div className="flex items-center gap-2 h-10 px-3 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading...
          </div>
        ) : (
          <Select
            value={experimentSelection}
            onChange={(e) => setExperimentSelection(e.target.value)}
            data-testid="select-experiment"
          >
            <option value={NO_EXPERIMENT}>— Not linked —</option>
            {(experiments ?? []).map((exp) => (
              <option key={exp.experiment_name} value={exp.experiment_name ?? ''}>
                {exp.experiment_name}
              </option>
            ))}
          </Select>
        )}
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>Back</Button>
        <Button
          onClick={handleContinue}
          disabled={!canContinue}
          data-testid="genomic-metadata-continue"
        >
          Continue
        </Button>
      </div>
    </div>
  )
}
