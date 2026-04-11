import { useState, useRef } from 'react'
import { Dropzone } from '@/components/upload/dropzone'
import type { FileWithPath } from '@/components/upload/dropzone'
import { detectFiles, formatFileSize } from '@/components/import-wizard/detection-engine'
import type { DetectionResult, DataCategory } from '@/components/import-wizard/detection-engine'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Loader2, FolderOpen, Calendar, FileType } from 'lucide-react'

interface StepDetectProps {
  onNext: (files: FileWithPath[], detection: DetectionResult) => void
}

const CATEGORY_LABELS: Record<DataCategory, string> = {
  drone_imagery: 'Drone Imagery',
  csv_tabular: 'CSV / Tabular',
  genomic: 'Genomic',
  thermal: 'Thermal',
  elevation: 'Elevation',
  mixed: 'Mixed',
}

export function StepDetect({ onNext }: StepDetectProps) {
  const [files, setFiles] = useState<FileWithPath[]>([])
  const [detection, setDetection] = useState<DetectionResult | null>(null)
  const [isDetecting, setIsDetecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const detectionCounterRef = useRef(0)

  async function handleFilesSelected(selectedFiles: FileWithPath[]) {
    setFiles(selectedFiles)
    setDetection(null)
    setError(null)
    setIsDetecting(true)

    const callId = ++detectionCounterRef.current

    try {
      const result = await detectFiles(selectedFiles)
      if (detectionCounterRef.current !== callId) return
      setDetection(result)
    } catch (err) {
      if (detectionCounterRef.current !== callId) return
      setError(err instanceof Error ? err.message : 'Detection failed')
    } finally {
      if (detectionCounterRef.current === callId) {
        setIsDetecting(false)
      }
    }
  }

  function handleContinue() {
    if (detection) {
      onNext(files, detection)
    }
  }

  function handleReset() {
    setFiles([])
    setDetection(null)
    setError(null)
  }

  return (
    <div className="space-y-6">
      {files.length === 0 ? (
        <Dropzone onFilesSelected={handleFilesSelected} />
      ) : (
        <>
          {/* Detection status */}
          {isDetecting && (
            <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Analyzing {files.length} files...</span>
            </div>
          )}

          {error && (
            <div className="rounded-md border border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive">
              {error}
            </div>
          )}

          {detection && (
            <div className="space-y-6">
              {/* Summary header */}
              <div className="rounded-lg border p-4 space-y-3" data-testid="detection-summary">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium">Detection Summary</h3>
                  <Button variant="ghost" size="sm" onClick={handleReset}>
                    Choose different files
                  </Button>
                </div>

                <div className="flex flex-wrap gap-2">
                  {detection.dataCategories.map((cat) => (
                    <Badge key={cat}>{CATEGORY_LABELS[cat]}</Badge>
                  ))}
                  <Badge variant="secondary">
                    {detection.totalFiles} files
                  </Badge>
                  <Badge variant="secondary">
                    {formatFileSize(detection.totalSize)}
                  </Badge>
                </div>

                {/* Detected dates */}
                {detection.detectedDates.length > 0 && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <Calendar className="w-4 h-4 text-muted-foreground shrink-0" />
                    <span className="text-sm text-muted-foreground">Dates:</span>
                    {detection.detectedDates.map((date) => (
                      <Badge key={date} variant="outline">{date}</Badge>
                    ))}
                  </div>
                )}

                {/* Suggestions */}
                {(detection.suggestedExperimentName || detection.suggestedSensorType || detection.suggestedPlatform) && (
                  <div className="text-sm space-y-1 text-muted-foreground">
                    {detection.suggestedExperimentName && (
                      <p>Suggested experiment: <span className="text-foreground font-medium">{detection.suggestedExperimentName}</span></p>
                    )}
                    {detection.suggestedPlatform && (
                      <p>Suggested platform: <span className="text-foreground font-medium">{detection.suggestedPlatform}</span></p>
                    )}
                    {detection.suggestedSensorType && (
                      <p>Suggested sensor: <span className="text-foreground font-medium">{detection.suggestedSensorType}</span></p>
                    )}
                  </div>
                )}
              </div>

              {/* File groups table */}
              {detection.fileGroups.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium flex items-center gap-1.5">
                    <FolderOpen className="w-4 h-4" />
                    File Groups
                  </h4>
                  <div className="rounded-md border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-muted/50">
                          <th className="text-left p-2 font-medium">Folder</th>
                          <th className="text-right p-2 font-medium">Files</th>
                          <th className="text-right p-2 font-medium">Size</th>
                          <th className="text-left p-2 font-medium">Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detection.fileGroups.map((group) => (
                          <tr key={group.folder} className="border-b last:border-0">
                            <td className="p-2 truncate max-w-[300px]" title={group.folder}>
                              {group.folder}
                            </td>
                            <td className="p-2 text-right text-muted-foreground">{group.fileCount}</td>
                            <td className="p-2 text-right text-muted-foreground">{formatFileSize(group.totalSize)}</td>
                            <td className="p-2">
                              {group.date ? (
                                <Badge variant="outline" className="text-xs">{group.date}</Badge>
                              ) : (
                                <span className="text-muted-foreground">--</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* CSV files */}
              {detection.csvFiles.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium flex items-center gap-1.5">
                    <FileType className="w-4 h-4" />
                    CSV Files
                  </h4>
                  <div className="space-y-2">
                    {detection.csvFiles.map((csv) => (
                      <div key={csv.name} className="rounded-md border p-3 space-y-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">{csv.name}</span>
                          <Badge variant="secondary" className="text-xs">
                            {csv.category.replace(/_/g, ' ')}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground truncate">
                          Headers: {csv.headers.join(', ')}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Continue button */}
              <div className="flex justify-end">
                <Button onClick={handleContinue} data-testid="detect-continue">Continue</Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
