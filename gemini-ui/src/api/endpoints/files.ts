import { get, post, del, postForm, getBlob, postBlob } from '@/api/client'
import type {
  FileMetadata,
  PaginatedFileList,
  ChunkStatusResponse,
  PresignedUrlResponse,
} from '@/api/types'

export const filesApi = {
  upload: (formData: FormData) =>
    postForm<FileMetadata>('api/files/upload', formData),

  uploadChunk: (formData: FormData) =>
    postForm<ChunkStatusResponse>('api/files/upload_chunk', formData),

  checkChunks: (data: { file_identifier: string; total_chunks: number }) =>
    post<ChunkStatusResponse>('api/files/check_uploaded_chunks', data),

  clearUploadCache: (data: { file_identifier: string }) =>
    post<void>('api/files/clear_upload_cache', data),

  getMetadata: (path: string) =>
    get<FileMetadata>(`api/files/metadata/${path}`),

  listFiles: (path: string) =>
    get<FileMetadata[]>(`api/files/list/${path}`),

  listNested: () =>
    get<unknown>('api/files/list_nested'),

  download: (path: string) =>
    getBlob(`api/files/download/${path}`),

  presign: (path: string) =>
    get<PresignedUrlResponse>(`api/files/presign/${path}`),

  deleteFile: (path: string) =>
    del(`api/files/delete/${path}`),

  downloadZip: (paths: string[]) =>
    postBlob('api/files/download_zip', { files: paths }),

  listFilesPaginated: (path: string, limit = 50, offset = 0) =>
    get<PaginatedFileList>(`api/files/list_paginated/${path}`, { limit, offset }),

  thumbnailUrl: (path: string, size = 200) =>
    `/api/files/thumbnail/${path}?size=${size}`,
}
