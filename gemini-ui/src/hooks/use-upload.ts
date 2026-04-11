import { useState, useCallback, useRef } from 'react'
import { api } from '@/api/client'
import type { FileWithPath } from '@/components/upload/dropzone'

const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB
const MAX_CONCURRENT = 3

export interface UploadFileStatus {
  file: FileWithPath
  objectName: string
  progress: number
  status: 'pending' | 'uploading' | 'complete' | 'error'
  error?: string
}

export interface UploadState {
  files: UploadFileStatus[]
  overallProgress: number
  isUploading: boolean
  completedCount: number
  errorCount: number
}

interface UseUploadOptions {
  onFileComplete?: (file: FileWithPath, objectName: string) => void
  onAllComplete?: () => void
  onError?: (file: FileWithPath, error: string) => void
}

export function useUpload(options: UseUploadOptions = {}) {
  const [state, setState] = useState<UploadState>({
    files: [],
    overallProgress: 0,
    isUploading: false,
    completedCount: 0,
    errorCount: 0,
  })
  const abortRef = useRef(false)
  const abortControllerRef = useRef<AbortController | null>(null)
  const optionsRef = useRef(options)
  optionsRef.current = options

  const updateFileStatus = useCallback((objectName: string, updates: Partial<UploadFileStatus>) => {
    setState((prev) => {
      const files = prev.files.map((f) =>
        f.objectName === objectName ? { ...f, ...updates } : f,
      )
      const completed = files.filter((f) => f.status === 'complete').length
      const errors = files.filter((f) => f.status === 'error').length
      const totalProgress = files.reduce((sum, f) => sum + f.progress, 0)
      return {
        ...prev,
        files,
        completedCount: completed,
        errorCount: errors,
        overallProgress: files.length > 0 ? totalProgress / files.length : 0,
      }
    })
  }, [])

  async function uploadSingleFile(file: FileWithPath, objectName: string, signal: AbortSignal): Promise<void> {
    if (file.size <= CHUNK_SIZE) {
      // Small file: direct upload
      const formData = new FormData()
      formData.append('file', file)
      formData.append('object_name', objectName)
      formData.append('bucket_name', 'gemini')
      await api.post('api/files/upload', { body: formData, signal })
      updateFileStatus(objectName, { progress: 100, status: 'complete' })
      optionsRef.current.onFileComplete?.(file, objectName)
      return
    }

    // Chunked upload
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE)
    const fileIdentifier = `${file.name}-${file.size}-${file.lastModified}`

    // Check for previously uploaded chunks
    let uploadedChunks = new Set<number>()
    try {
      const checkRes = await api.post('api/files/check_uploaded_chunks', {
        json: { file_identifier: fileIdentifier, total_chunks: totalChunks },
        signal,
      }).json<{ uploaded_chunks: number[] }>()
      uploadedChunks = new Set(checkRes.uploaded_chunks)
    } catch {
      // No previous chunks
    }

    for (let i = 0; i < totalChunks; i++) {
      if (abortRef.current) return
      if (uploadedChunks.has(i)) {
        updateFileStatus(objectName, { progress: ((i + 1) / totalChunks) * 100 })
        continue
      }

      const start = i * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, file.size)
      const chunk = file.slice(start, end)

      const formData = new FormData()
      formData.append('file_chunk', new File([chunk], file.name))
      formData.append('chunk_index', String(i))
      formData.append('total_chunks', String(totalChunks))
      formData.append('file_identifier', fileIdentifier)
      formData.append('object_name', objectName)
      formData.append('bucket_name', 'gemini')

      await api.post('api/files/upload_chunk', { body: formData, signal })
      updateFileStatus(objectName, { progress: ((i + 1) / totalChunks) * 100 })
    }

    updateFileStatus(objectName, { progress: 100, status: 'complete' })
    optionsRef.current.onFileComplete?.(file, objectName)
  }

  const startUpload = useCallback(
    async (fileMap: Array<{ file: FileWithPath; objectName: string }>) => {
      abortRef.current = false
      abortControllerRef.current?.abort()
      const controller = new AbortController()
      abortControllerRef.current = controller

      const initialFiles: UploadFileStatus[] = fileMap.map(({ file, objectName }) => ({
        file,
        objectName,
        progress: 0,
        status: 'pending' as const,
      }))

      setState({
        files: initialFiles,
        overallProgress: 0,
        isUploading: true,
        completedCount: 0,
        errorCount: 0,
      })

      // Process with concurrency limit
      const queue = [...fileMap]
      const running: Promise<void>[] = []

      async function processNext(): Promise<void> {
        if (abortRef.current || queue.length === 0) return
        const item = queue.shift()!
        updateFileStatus(item.objectName, { status: 'uploading' })

        try {
          await uploadSingleFile(item.file, item.objectName, controller.signal)
        } catch (err) {
          if (err instanceof DOMException && err.name === 'AbortError') return
          const errorMsg = err instanceof Error ? err.message : 'Upload failed'
          updateFileStatus(item.objectName, { status: 'error', error: errorMsg })
          optionsRef.current.onError?.(item.file, errorMsg)
        }

        return processNext()
      }

      for (let i = 0; i < Math.min(MAX_CONCURRENT, fileMap.length); i++) {
        running.push(processNext())
      }

      await Promise.all(running)
      setState((prev) => ({ ...prev, isUploading: false }))
      optionsRef.current.onAllComplete?.()
    },
    [updateFileStatus],
  )

  const abort = useCallback(() => {
    abortRef.current = true
    abortControllerRef.current?.abort()
  }, [])

  const reset = useCallback(() => {
    abortRef.current = false
    setState({
      files: [],
      overallProgress: 0,
      isUploading: false,
      completedCount: 0,
      errorCount: 0,
    })
  }, [])

  return { state, startUpload, abort, reset }
}
