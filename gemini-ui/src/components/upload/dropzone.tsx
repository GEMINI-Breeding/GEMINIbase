import { useCallback, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import { cn } from '@/lib/utils'
import { Upload, FolderOpen } from 'lucide-react'
import { Button } from '@/components/ui/button'

export interface FileWithPath extends File {
  path?: string
}

export interface FileTreeNode {
  name: string
  path: string
  isDirectory: boolean
  children: FileTreeNode[]
  file?: FileWithPath
}

interface DropzoneProps {
  onFilesSelected: (files: FileWithPath[]) => void
  accept?: Record<string, string[]>
  disabled?: boolean
  className?: string
}

function buildFileTree(files: FileWithPath[]): FileTreeNode {
  const root: FileTreeNode = { name: 'root', path: '', isDirectory: true, children: [] }

  for (const file of files) {
    const relativePath = file.path || (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name
    const parts = relativePath.replace(/^\//, '').split('/')
    let current = root

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const isLast = i === parts.length - 1

      if (isLast) {
        current.children.push({
          name: part,
          path: relativePath,
          isDirectory: false,
          children: [],
          file,
        })
      } else {
        let dir = current.children.find((c) => c.isDirectory && c.name === part)
        if (!dir) {
          dir = {
            name: part,
            path: parts.slice(0, i + 1).join('/'),
            isDirectory: true,
            children: [],
          }
          current.children.push(dir)
        }
        current = dir
      }
    }
  }

  return root
}

export { buildFileTree }

export function Dropzone({ onFilesSelected, accept, disabled, className }: DropzoneProps) {
  const dirInputRef = useRef<HTMLInputElement>(null)

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      onFilesSelected(acceptedFiles as FileWithPath[])
    },
    [onFilesSelected],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    noClick: false,
    disabled,
    accept,
  })

  const handleDirectorySelect = () => {
    dirInputRef.current?.click()
  }

  const handleDirectoryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList) return
    const files: FileWithPath[] = []
    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i] as FileWithPath
      file.path = (fileList[i] as File & { webkitRelativePath?: string }).webkitRelativePath || file.name
      files.push(file)
    }
    onFilesSelected(files)
    e.target.value = ''
  }

  return (
    <div className={className}>
      <div
        {...getRootProps()}
        data-testid="dropzone"
        className={cn(
          'border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors',
          isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50',
          disabled && 'opacity-50 cursor-not-allowed',
        )}
      >
        <input {...getInputProps()} />
        <Upload className="w-10 h-10 mx-auto mb-4 text-muted-foreground" />
        {isDragActive ? (
          <p className="text-primary font-medium">Drop files here...</p>
        ) : (
          <>
            <p className="font-medium mb-1">Drag & drop files here, or click to select</p>
            <p className="text-sm text-muted-foreground">
              Supports CSV, images, VCF, HapMap, and other data files
            </p>
          </>
        )}
      </div>

      <div className="mt-3 flex justify-center">
        <Button type="button" variant="outline" size="sm" onClick={handleDirectorySelect} disabled={disabled} data-testid="select-folder-btn">
          <FolderOpen className="w-4 h-4 mr-1" />
          Select Folder
        </Button>
        <input
          ref={dirInputRef}
          type="file"
          className="hidden"
          onChange={handleDirectoryChange}
          {...({ webkitdirectory: '', directory: '', mozdirectory: '' } as React.InputHTMLAttributes<HTMLInputElement>)}
        />
      </div>
    </div>
  )
}
