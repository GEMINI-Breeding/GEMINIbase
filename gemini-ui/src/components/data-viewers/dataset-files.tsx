import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { filesApi } from '@/api/endpoints/files'
import type { FileMetadata } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Download, Image, FileText, FileSpreadsheet, File, Loader2, ChevronLeft, ChevronRight } from 'lucide-react'

const PAGE_SIZE = 50

interface DatasetFilesProps {
  filesPrefix: string | null
}

function getFileIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  if (['jpg', 'jpeg', 'png', 'gif', 'tif', 'tiff', 'svg'].includes(ext)) return Image
  if (['csv', 'tsv', 'xls', 'xlsx'].includes(ext)) return FileSpreadsheet
  if (['txt', 'json', 'xml', 'yaml', 'yml'].includes(ext)) return FileText
  return File
}

function isImageFile(name: string) {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  return ['jpg', 'jpeg', 'png', 'gif', 'svg'].includes(ext)
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getDownloadUrl(file: FileMetadata): string {
  return `/api/files/download/${file.bucket_name}/${file.object_name}`
}

function getThumbnailUrl(file: FileMetadata): string {
  return filesApi.thumbnailUrl(`${file.bucket_name}/${file.object_name}`, 200)
}

function getFileName(objectName: string): string {
  return objectName.split('/').pop() || objectName
}

export function DatasetFiles({ filesPrefix }: DatasetFilesProps) {
  const [offset, setOffset] = useState(0)

  const { data, isLoading, error } = useQuery({
    queryKey: ['dataset-files-paginated', filesPrefix, offset],
    queryFn: () => filesApi.listFilesPaginated(filesPrefix!, PAGE_SIZE, offset),
    enabled: !!filesPrefix,
    retry: 1,
  })

  if (!filesPrefix) {
    return (
      <div className="text-center py-8 text-muted-foreground" data-testid="dataset-files-empty">
        <File className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p>No file location stored for this dataset.</p>
        <p className="text-sm mt-1">Files uploaded via the import wizard will appear here.</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8 text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        Loading files...
      </div>
    )
  }

  if (error || !data || data.total_count === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground" data-testid="dataset-files-empty">
        <File className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p>No files found at this location.</p>
      </div>
    )
  }

  const { files, total_count } = data
  const imageFiles = files.filter((f) => isImageFile(f.object_name))
  const otherFiles = files.filter((f) => !isImageFile(f.object_name))
  const totalPages = Math.ceil(total_count / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1
  const rangeStart = offset + 1
  const rangeEnd = Math.min(offset + PAGE_SIZE, total_count)

  return (
    <div className="space-y-6" data-testid="dataset-files">
      {/* Summary + pagination controls */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground" data-testid="file-count">
          {total_count === 1
            ? '1 file'
            : `${rangeStart}-${rangeEnd} of ${total_count} files`}
        </p>
        {totalPages > 1 && (
          <div className="flex items-center gap-2" data-testid="pagination-controls">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              data-testid="page-prev"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="text-sm text-muted-foreground">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={offset + PAGE_SIZE >= total_count}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              data-testid="page-next"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        )}
      </div>

      {/* Image gallery with thumbnails */}
      {imageFiles.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium">Images ({imageFiles.length} on this page)</h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3" data-testid="image-gallery">
            {imageFiles.map((file) => (
              <a
                key={file.object_name}
                href={getDownloadUrl(file)}
                target="_blank"
                rel="noopener noreferrer"
                className="group relative rounded-lg border overflow-hidden hover:border-primary transition-colors"
                data-testid="image-thumbnail"
              >
                <div className="aspect-square bg-muted flex items-center justify-center">
                  <img
                    src={getThumbnailUrl(file)}
                    alt={getFileName(file.object_name)}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                </div>
                <div className="p-1.5">
                  <p className="text-xs truncate" title={getFileName(file.object_name)}>
                    {getFileName(file.object_name)}
                  </p>
                  <p className="text-[10px] text-muted-foreground">{formatSize(file.size || 0)}</p>
                </div>
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center">
                  <Download className="w-5 h-5 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow" />
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Other files */}
      {otherFiles.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium">Other Files ({otherFiles.length} on this page)</h4>
          <div className="rounded-md border divide-y" data-testid="file-list">
            {otherFiles.map((file) => {
              const Icon = getFileIcon(file.object_name)
              return (
                <div
                  key={file.object_name}
                  className="flex items-center gap-3 px-3 py-2 hover:bg-muted/50 transition-colors"
                  data-testid="file-row"
                >
                  <Icon className="w-4 h-4 text-muted-foreground shrink-0" />
                  <span className="text-sm truncate flex-1" title={getFileName(file.object_name)}>
                    {getFileName(file.object_name)}
                  </span>
                  <span className="text-xs text-muted-foreground shrink-0">
                    {formatSize(file.size || 0)}
                  </span>
                  <a href={getDownloadUrl(file)} target="_blank" rel="noopener noreferrer" className="shrink-0 p-1 rounded hover:bg-muted">
                    <Download className="w-3.5 h-3.5" />
                  </a>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
