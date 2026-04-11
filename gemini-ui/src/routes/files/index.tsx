import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { filesApi } from '@/api/endpoints/files'
import {
  FolderOpen, File, ChevronRight, ChevronDown,
  Download, Image, FileText, FileSpreadsheet,
  RefreshCw, Eye,
} from 'lucide-react'

export const Route = createFileRoute('/files/')({
  component: FileBrowser,
})

interface TreeNode {
  name: string
  path: string
  isDir: boolean
  children: TreeNode[]
  metadata?: { size: number; content_type?: string; last_modified?: string }
}

function buildTree(files: Array<{ object_name: string; size?: number; content_type?: string; last_modified?: string }>): TreeNode {
  const root: TreeNode = { name: 'Files', path: '', isDir: true, children: [] }

  for (const file of files) {
    const parts = file.object_name.split('/').filter(Boolean)
    let current = root

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const isLast = i === parts.length - 1
      const path = parts.slice(0, i + 1).join('/')

      if (isLast && !file.object_name.endsWith('/')) {
        current.children.push({
          name: part,
          path,
          isDir: false,
          children: [],
          metadata: { size: file.size || 0, content_type: file.content_type, last_modified: file.last_modified },
        })
      } else {
        let dir = current.children.find((c) => c.isDir && c.name === part)
        if (!dir) {
          dir = { name: part, path, isDir: true, children: [] }
          current.children.push(dir)
        }
        current = dir
      }
    }
  }

  return root
}

function getFileIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase()
  if (['jpg', 'jpeg', 'png', 'gif', 'tif', 'tiff', 'svg'].includes(ext || '')) return Image
  if (['csv', 'tsv', 'xls', 'xlsx'].includes(ext || '')) return FileSpreadsheet
  return FileText
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function TreeItem({
  node,
  depth,
  selectedPath,
  onSelect,
}: {
  node: TreeNode
  depth: number
  selectedPath: string | null
  onSelect: (node: TreeNode) => void
}) {
  const [expanded, setExpanded] = useState(depth < 2)
  const isSelected = selectedPath === node.path

  if (node.isDir) {
    return (
      <div>
        <button
          onClick={() => { setExpanded(!expanded); onSelect(node) }}
          className={cn(
            'flex items-center gap-1 w-full text-left text-sm py-1 px-1 rounded hover:bg-muted transition-colors',
            isSelected && 'bg-muted',
          )}
          style={{ paddingLeft: depth * 16 }}
        >
          {expanded ? <ChevronDown className="w-3.5 h-3.5 shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 shrink-0" />}
          <FolderOpen className="w-4 h-4 text-accent shrink-0" />
          <span className="truncate">{node.name}</span>
          <Badge variant="secondary" className="ml-auto text-[10px]">{node.children.length}</Badge>
        </button>
        {expanded && node.children
          .sort((a, b) => (a.isDir === b.isDir ? a.name.localeCompare(b.name) : a.isDir ? -1 : 1))
          .map((child) => (
            <TreeItem key={child.path} node={child} depth={depth + 1} selectedPath={selectedPath} onSelect={onSelect} />
          ))}
      </div>
    )
  }

  const Icon = getFileIcon(node.name)
  return (
    <button
      onClick={() => onSelect(node)}
      className={cn(
        'flex items-center gap-1 w-full text-left text-sm py-1 px-1 rounded hover:bg-muted transition-colors',
        isSelected && 'bg-primary/10',
      )}
      style={{ paddingLeft: depth * 16 }}
    >
      <div className="w-3.5" />
      <Icon className="w-4 h-4 text-muted-foreground shrink-0" />
      <span className="truncate">{node.name}</span>
      {node.metadata && (
        <span className="text-xs text-muted-foreground ml-auto shrink-0">{formatSize(node.metadata.size)}</span>
      )}
    </button>
  )
}

function FilePreview({ node }: { node: TreeNode }) {
  const ext = node.name.split('.').pop()?.toLowerCase()
  const isImage = ['jpg', 'jpeg', 'png', 'gif', 'svg'].includes(ext || '')

  const presignQuery = useQuery({
    queryKey: ['presign', node.path],
    queryFn: () => filesApi.presign(node.path),
    enabled: isImage,
  })

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <h3 className="font-medium text-sm truncate">{node.name}</h3>
      {node.metadata && (
        <div className="text-xs text-muted-foreground space-y-1">
          <p>Size: {formatSize(node.metadata.size)}</p>
          {node.metadata.content_type && <p>Type: {node.metadata.content_type}</p>}
          {node.metadata.last_modified && <p>Modified: {new Date(node.metadata.last_modified).toLocaleString()}</p>}
        </div>
      )}
      {isImage && presignQuery.data && (
        <img src={presignQuery.data.url} alt={node.name} className="max-w-full max-h-64 rounded border object-contain" />
      )}
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={() => window.open(`/api/files/download/${node.path}`, '_blank')}>
          <Download className="w-3.5 h-3.5 mr-1" /> Download
        </Button>
        {isImage && presignQuery.data && (
          <Button size="sm" variant="outline" onClick={() => window.open(presignQuery.data.url, '_blank')}>
            <Eye className="w-3.5 h-3.5 mr-1" /> Full Size
          </Button>
        )}
      </div>
    </div>
  )
}

function FileBrowser() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<TreeNode | null>(null)

  const { data: files, isLoading } = useQuery({
    queryKey: ['files', 'nested'],
    queryFn: () => filesApi.listNested(),
  })

  const tree = files ? buildTree(files as Array<{ object_name: string; size?: number; content_type?: string; last_modified?: string }>) : null

  return (
    <div>
      <PageHeader
        title="Files"
        description="Browse files stored in MinIO"
        actions={
          <Button variant="outline" size="sm" onClick={() => queryClient.invalidateQueries({ queryKey: ['files'] })}>
            <RefreshCw className="w-4 h-4 mr-1" /> Refresh
          </Button>
        }
      />

      {isLoading && (
        <div className="text-center py-12 text-muted-foreground">Loading file tree...</div>
      )}

      {!isLoading && !tree?.children.length && (
        <div className="text-center py-12">
          <File className="w-12 h-12 mx-auto mb-3 text-muted-foreground" />
          <p className="text-muted-foreground">No files found</p>
          <p className="text-sm text-muted-foreground mt-1">Upload data via the Import page</p>
        </div>
      )}

      {tree && tree.children.length > 0 && (
        <div className="flex gap-4 h-[calc(100vh-200px)]">
          <div className="w-80 border rounded-lg overflow-auto p-2 shrink-0">
            {tree.children
              .sort((a, b) => (a.isDir === b.isDir ? a.name.localeCompare(b.name) : a.isDir ? -1 : 1))
              .map((child) => (
                <TreeItem
                  key={child.path}
                  node={child}
                  depth={0}
                  selectedPath={selected?.path || null}
                  onSelect={setSelected}
                />
              ))}
          </div>

          <div className="flex-1 overflow-auto">
            {!selected && (
              <div className="text-center py-12 text-muted-foreground text-sm">
                Select a file to preview
              </div>
            )}
            {selected && !selected.isDir && <FilePreview node={selected} />}
            {selected && selected.isDir && (
              <div className="space-y-2">
                <h3 className="font-medium">{selected.name}</h3>
                <p className="text-sm text-muted-foreground">{selected.children.length} items</p>
                <div className="border rounded-lg divide-y">
                  {selected.children
                    .sort((a, b) => (a.isDir === b.isDir ? a.name.localeCompare(b.name) : a.isDir ? -1 : 1))
                    .map((child) => {
                      const Icon = child.isDir ? FolderOpen : getFileIcon(child.name)
                      return (
                        <button
                          key={child.path}
                          className="flex items-center gap-2 w-full text-left px-3 py-2 hover:bg-muted text-sm"
                          onClick={() => setSelected(child)}
                        >
                          <Icon className={cn('w-4 h-4', child.isDir ? 'text-accent' : 'text-muted-foreground')} />
                          <span className="flex-1 truncate">{child.name}</span>
                          {!child.isDir && child.metadata && (
                            <span className="text-xs text-muted-foreground">{formatSize(child.metadata.size)}</span>
                          )}
                          {child.isDir && (
                            <Badge variant="secondary" className="text-[10px]">{child.children.length}</Badge>
                          )}
                        </button>
                      )
                    })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
