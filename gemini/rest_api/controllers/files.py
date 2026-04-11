import io
import os
import tempfile
import hashlib

from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body, Parameter
from litestar.controller import Controller
from litestar.response import Stream
from litestar.enums import RequestEncodingType

from urllib3.response import HTTPResponse
from mimetypes import guess_type

from gemini.rest_api.models import (
    RESTAPIError,
    FileMetadata,
    PaginatedFileList,
    UploadFileRequest,
    ChunkUploadRequest,
    ChunkStatusResponse,
    PresignedUrlResponse,
)

from gemini.manager import GEMINIManager, GEMINIComponentType
from gemini.storage.providers.minio_storage import MinioStorageProvider
from gemini.storage.config.storage_config import MinioStorageConfig

from typing import Annotated, List

# In-memory tracking of chunked uploads: { file_identifier: { chunk_index: temp_path, ... } }
_chunk_uploads: dict[str, dict[int, str]] = {}

manager = GEMINIManager()
minio_storage_settings = manager.get_component_settings(GEMINIComponentType.STORAGE)
minio_storage_config = MinioStorageConfig(
    endpoint=f"{minio_storage_settings['GEMINI_STORAGE_HOSTNAME']}:{minio_storage_settings['GEMINI_STORAGE_PORT']}",
    access_key=minio_storage_settings['GEMINI_STORAGE_ACCESS_KEY'],
    secret_key=minio_storage_settings['GEMINI_STORAGE_SECRET_KEY'],
    bucket_name=minio_storage_settings['GEMINI_STORAGE_BUCKET_NAME'],
    secure=False
)
minio_storage_provider = MinioStorageProvider(minio_storage_config)

class FileController(Controller):

    @get(path="/metadata/{file_path:path}", sync_to_thread=True)
    def get_file_metadata(
        self,
        file_path: str
    ) -> FileMetadata:
        try:
            bucket_name = file_path.split('/')[1]
            if not minio_storage_provider.bucket_exists(bucket_name):
                error = RESTAPIError(
                    error="Bucket not found",
                    error_description=f"Bucket {bucket_name} does not exist"
                )
                return Response(content=error, status_code=404)
            object_name = '/'.join(file_path.split('/')[2:])
            file_exists = minio_storage_provider.file_exists(
                object_name=object_name,
                bucket_name=bucket_name
            )
            if not file_exists:
                error = RESTAPIError(
                    error="File not found",
                    error_description=f"File {file_path} does not exist"
                )
                return Response(content=error, status_code=404)
            file_info = minio_storage_provider.get_file_metadata(
                object_name=object_name,
                bucket_name=bucket_name
            )
            return FileMetadata(
                bucket_name=file_info['bucket_name'],
                object_name=file_info['object_name'],
                size=file_info['size'],
                last_modified=file_info['last_modified'],
                content_type=file_info['content_type'],
                etag=file_info['etag']
            )
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving file metadata"
            )
            return Response(content=error, status_code=500)
        
    @get(path="/list/{file_path:path}", sync_to_thread=True)
    def list_files(
        self,
        file_path: str
    ) -> List[FileMetadata]:
        try:
            bucket_name = file_path.split('/')[1]
            if not minio_storage_provider.bucket_exists(bucket_name):
                error = RESTAPIError(
                    error="Bucket not found",
                    error_description=f"Bucket {bucket_name} does not exist"
                )
                return Response(content=error, status_code=404)
            prefix = '/'.join(file_path.split('/')[2:])
            object_names = minio_storage_provider.list_files(
                bucket_name=bucket_name,
                prefix=prefix
            )
            if not object_names:
                return []
            # Convert object names to FileMetadata
            file_metadata_list = []
            for object_name in object_names:
                file_info = minio_storage_provider.get_file_metadata(
                    object_name=object_name,
                    bucket_name=bucket_name
                )
                file_metadata = FileMetadata(
                    bucket_name=file_info['bucket_name'],
                    object_name=file_info['object_name'],
                    size=file_info['size'],
                    last_modified=file_info['last_modified'],
                    content_type=file_info['content_type'],
                    etag=file_info['etag']
                )
                file_metadata_list.append(file_metadata)
            return file_metadata_list
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while listing files"
            )
            return Response(content=error, status_code=500)
        
    @get(path="/download/{file_path:path}", sync_to_thread=True)
    def download_file(
        self,
        file_path: str
    ) -> Stream:
        try:
            bucket_name = file_path.split('/')[1]
            if not minio_storage_provider.bucket_exists(bucket_name):
                error = RESTAPIError(
                    error="Bucket not found",
                    error_description=f"Bucket {bucket_name} does not exist"
                )
                return Response(content=error, status_code=404)
            object_name = '/'.join(file_path.split('/')[2:])
            file_name = object_name.split('/')[-1]
            file_exists = minio_storage_provider.file_exists(
                object_name=object_name,
                bucket_name=bucket_name
            )
            if not file_exists:
                error = RESTAPIError(
                    error="File not found",
                    error_description=f"File {file_path} does not exist"
                )
                return Response(content=error, status_code=404)
            file_stream = minio_storage_provider.download_file_stream(
                object_name=object_name,
                bucket_name=bucket_name
            )
            return Stream(
                content=file_stream.stream(),
                media_type=guess_type(file_name)[0] or "application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={file_name}"}
            )
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while downloading the file"
            )
            return Response(content=error, status_code=500)
        
    @post(path="/upload", sync_to_thread=True)
    def upload_file(
        self,
        data: Annotated[UploadFileRequest, Body(media_type=RequestEncodingType.MULTI_PART)]
    ) -> FileMetadata:
        try:
            bucket_name = data.bucket_name
            if not minio_storage_provider.bucket_exists(bucket_name):
                error = RESTAPIError(
                    error="Bucket not found",
                    error_description=f"Bucket {bucket_name} does not exist"
                )
                return Response(content=error, status_code=404)
            file_stream = data.file.file
            minio_storage_provider.upload_file(
                bucket_name=bucket_name,
                object_name=data.object_name,
                data_stream=file_stream
            )
            file_info = minio_storage_provider.get_file_metadata(
                object_name=data.object_name,
                bucket_name=bucket_name
            )
            return FileMetadata(
                bucket_name=file_info['bucket_name'],
                object_name=file_info['object_name'],
                size=file_info['size'],
                last_modified=file_info['last_modified'],
                content_type=file_info['content_type'],
                etag=file_info['etag']
            )
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while uploading the file"
            )
            return Response(content=error_message, status_code=500)
        
    
        
    @delete(path="/delete/{file_path:path}", sync_to_thread=True)
    def delete_file(
        self,
        file_path: str
    ) -> None:
        """
        Delete a file or all files under a prefix from MinIO.

        Tries exact file match first. If not found, treats the path as a
        directory prefix and deletes all objects under it (MinIO has no
        real directories — a "dataset folder" is just a shared key prefix).
        """
        try:
            bucket_name = file_path.split('/')[1]
            if not minio_storage_provider.bucket_exists(bucket_name):
                error = RESTAPIError(
                    error="Bucket not found",
                    error_description=f"Bucket {bucket_name} does not exist"
                )
                return Response(content=error, status_code=404)
            object_name = '/'.join(file_path.split('/')[2:])

            # Try exact file first
            file_exists = minio_storage_provider.file_exists(
                object_name=object_name,
                bucket_name=bucket_name
            )
            if file_exists:
                is_deleted = minio_storage_provider.delete_file(
                    object_name=object_name,
                    bucket_name=bucket_name
                )
                if not is_deleted:
                    return Response(
                        content=RESTAPIError(
                            error="File deletion failed",
                            error_description=f"Failed to delete file {file_path}"
                        ),
                        status_code=500,
                    )
                return None

            # Not an exact file — treat as prefix and delete all objects under it
            prefix = object_name.rstrip('/') + '/'
            objects = minio_storage_provider.list_files(
                prefix=prefix, recursive=True, bucket_name=bucket_name
            )
            if not objects:
                return Response(
                    content=RESTAPIError(
                        error="Not found",
                        error_description=f"No files found at {file_path}"
                    ),
                    status_code=404,
                )
            deleted_count = 0
            for obj_name in objects:
                try:
                    minio_storage_provider.delete_file(
                        object_name=obj_name, bucket_name=bucket_name
                    )
                    deleted_count += 1
                except Exception:
                    pass
            if deleted_count == 0:
                return Response(
                    content=RESTAPIError(
                        error="Deletion failed",
                        error_description=f"Failed to delete any files under {file_path}"
                    ),
                    status_code=500,
                )
            return None
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the file"
            )
            return Response(content=error_message, status_code=500)

    @post(path="/upload_chunk", sync_to_thread=True)
    def upload_chunk(
        self,
        data: Annotated[ChunkUploadRequest, Body(media_type=RequestEncodingType.MULTI_PART)]
    ) -> ChunkStatusResponse:
        """Receive a single chunk of a multi-part file upload.
        When all chunks are received, assembles and uploads to MinIO."""
        try:
            file_id = data.file_identifier
            chunk_idx = data.chunk_index
            total = data.total_chunks

            # Save chunk to temp file
            if file_id not in _chunk_uploads:
                _chunk_uploads[file_id] = {}

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".chunk{chunk_idx}")
            chunk_data = data.file_chunk.file.read()
            tmp.write(chunk_data)
            tmp.close()
            _chunk_uploads[file_id][chunk_idx] = tmp.name

            uploaded = len(_chunk_uploads[file_id])

            # If all chunks received, assemble and upload
            if uploaded == total:
                bucket_name = data.bucket_name or minio_storage_config.bucket_name
                assembled = tempfile.NamedTemporaryFile(delete=False, suffix=".assembled")
                for i in range(total):
                    chunk_path = _chunk_uploads[file_id][i]
                    with open(chunk_path, 'rb') as cf:
                        assembled.write(cf.read())
                    os.unlink(chunk_path)
                assembled.close()

                minio_storage_provider.upload_file(
                    bucket_name=bucket_name,
                    object_name=data.object_name,
                    input_file_path=assembled.name,
                )
                os.unlink(assembled.name)
                del _chunk_uploads[file_id]

                return ChunkStatusResponse(
                    file_identifier=file_id,
                    uploaded_chunks=total,
                    total_chunks=total,
                    complete=True,
                )

            return ChunkStatusResponse(
                file_identifier=file_id,
                uploaded_chunks=uploaded,
                total_chunks=total,
                complete=False,
            )
        except Exception as e:
            # Clean up temp files on error
            if data.file_identifier in _chunk_uploads:
                for path in _chunk_uploads[data.file_identifier].values():
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
                del _chunk_uploads[data.file_identifier]
            return Response(
                content=RESTAPIError(error=str(e), error_description="Chunk upload failed"),
                status_code=500,
            )

    @post(path="/check_uploaded_chunks", sync_to_thread=True)
    def check_uploaded_chunks(
        self,
        data: dict,
    ) -> ChunkStatusResponse:
        """Check how many chunks have been uploaded for a given file identifier."""
        file_id = data.get("file_identifier", "")
        total = data.get("total_chunks", 0)
        chunks = _chunk_uploads.get(file_id, {})
        return ChunkStatusResponse(
            file_identifier=file_id,
            uploaded_chunks=len(chunks),
            total_chunks=total,
            complete=False,
        )

    @post(path="/clear_upload_cache", sync_to_thread=True)
    def clear_upload_cache(
        self,
        data: dict,
    ) -> dict:
        """Clear cached chunks for a file identifier."""
        file_id = data.get("file_identifier", "")
        if file_id in _chunk_uploads:
            for path in _chunk_uploads[file_id].values():
                try:
                    os.unlink(path)
                except OSError:
                    pass
            del _chunk_uploads[file_id]
        return {"status": "ok", "file_identifier": file_id}

    @get(path="/presign/{file_path:path}", sync_to_thread=True)
    def presign_url(
        self,
        file_path: str,
        expires_seconds: int = 3600,
    ) -> PresignedUrlResponse:
        """Generate a presigned URL for direct file access from MinIO."""
        try:
            bucket_name = file_path.split('/')[1]
            object_name = '/'.join(file_path.split('/')[2:])
            url = minio_storage_provider.get_download_url(
                object_name=object_name,
                bucket_name=bucket_name,
            )
            return PresignedUrlResponse(url=url, expires_in_seconds=expires_seconds)
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to generate presigned URL"),
                status_code=500,
            )

    @get(path="/list_nested", sync_to_thread=True)
    def list_dirs_nested(self) -> dict:
        """List all directories nested under Raw/ in a tree structure.
        Returns a dict of {year: {experiment: {location: {population: [dates]}}}}."""
        try:
            bucket = minio_storage_config.bucket_name
            items = minio_storage_provider.list_files(
                bucket_name=bucket, prefix="Raw/"
            )
            tree = {}
            for item in items:
                parts = item.object_name.split("/")
                # Raw/{year}/{experiment}/{location}/{population}/{date}/...
                if len(parts) >= 6:
                    year = parts[1]
                    experiment = parts[2]
                    location = parts[3]
                    population = parts[4]
                    date = parts[5]
                    tree.setdefault(year, {}).setdefault(experiment, {}).setdefault(
                        location, {}
                    ).setdefault(population, [])
                    if date not in tree[year][experiment][location][population]:
                        tree[year][experiment][location][population].append(date)
            return tree
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to list nested dirs"),
                status_code=500,
            )

    @get(path="/list_nested_processed", sync_to_thread=True)
    def list_dirs_nested_processed(self) -> dict:
        """List all directories nested under Processed/ in a tree structure."""
        try:
            bucket = minio_storage_config.bucket_name
            items = minio_storage_provider.list_files(
                bucket_name=bucket, prefix="Processed/"
            )
            tree = {}
            for item in items:
                parts = item.object_name.split("/")
                if len(parts) >= 6:
                    year = parts[1]
                    experiment = parts[2]
                    location = parts[3]
                    population = parts[4]
                    date = parts[5]
                    tree.setdefault(year, {}).setdefault(experiment, {}).setdefault(
                        location, {}
                    ).setdefault(population, [])
                    if date not in tree[year][experiment][location][population]:
                        tree[year][experiment][location][population].append(date)
            return tree
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to list nested processed dirs"),
                status_code=500,
            )

    @post(path="/download_zip", sync_to_thread=True)
    def download_zip(self, data: dict) -> Response:
        """Download multiple files as a ZIP archive."""
        import zipfile
        try:
            bucket = minio_storage_config.bucket_name
            files = data.get("files", [])
            prefix = data.get("prefix", "")

            if prefix and not files:
                # List all files under the prefix
                items = minio_storage_provider.list_files(
                    bucket_name=bucket, prefix=prefix
                )
                files = [item.object_name for item in items]

            if not files:
                return Response(
                    content=RESTAPIError(error="No files", error_description="No files to download"),
                    status_code=400,
                )

            # Create ZIP in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in files:
                    try:
                        stream = minio_storage_provider.download_file_stream(
                            object_name=file_path, bucket_name=bucket
                        )
                        content = stream.read()
                        stream.close()
                        stream.release_conn()
                        # Use just the filename in the zip
                        arcname = file_path.split("/")[-1]
                        zf.writestr(arcname, content)
                    except Exception:
                        continue

            zip_buffer.seek(0)

            return Stream(
                content=zip_buffer,
                media_type="application/zip",
                headers={"Content-Disposition": "attachment; filename=download.zip"},
            )
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to create zip"),
                status_code=500,
            )

    @get(path="/list_paginated/{file_path:path}", sync_to_thread=True)
    def list_files_paginated(
        self,
        file_path: str,
        limit: int = Parameter(default=50, ge=1, le=500),
        offset: int = Parameter(default=0, ge=0),
    ) -> PaginatedFileList:
        try:
            parts = file_path.split('/')
            bucket_name = parts[1] if len(parts) > 1 else parts[0]
            prefix = '/'.join(parts[2:]) if len(parts) > 2 else ''
            if not minio_storage_provider.bucket_exists(bucket_name):
                return Response(
                    content=RESTAPIError(error="Bucket not found", error_description=f"Bucket {bucket_name} does not exist"),
                    status_code=404,
                )
            result = minio_storage_provider.list_files_paginated(
                bucket_name=bucket_name,
                prefix=prefix,
                limit=limit,
                offset=offset,
            )
            files = [
                FileMetadata(
                    bucket_name=f['bucket_name'],
                    object_name=f['object_name'],
                    size=f['size'],
                    last_modified=f['last_modified'],
                    content_type=f.get('content_type'),
                    etag=f.get('etag', ''),
                )
                for f in result['files']
            ]
            return PaginatedFileList(
                files=files,
                total_count=result['total_count'],
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="An error occurred while listing files"),
                status_code=500,
            )

    @get(path="/thumbnail/{file_path:path}", sync_to_thread=True)
    def get_thumbnail(
        self,
        file_path: str,
        size: int = Parameter(default=200, ge=32, le=800),
    ) -> Stream:
        try:
            from PIL import Image as PILImage

            parts = file_path.split('/')
            bucket_name = parts[1] if len(parts) > 1 else parts[0]
            object_name = '/'.join(parts[2:]) if len(parts) > 2 else ''

            # Check for cached thumbnail
            thumb_object = f".thumbnails/{size}/{object_name}"
            if minio_storage_provider.file_exists(object_name=thumb_object, bucket_name=bucket_name):
                thumb_stream = minio_storage_provider.download_file_stream(
                    object_name=thumb_object, bucket_name=bucket_name
                )
                return Stream(
                    content=thumb_stream.stream(),
                    media_type="image/webp",
                    headers={"Cache-Control": "public, max-age=86400"},
                )

            # Generate thumbnail
            file_stream = minio_storage_provider.download_file_stream(
                object_name=object_name, bucket_name=bucket_name
            )
            img = PILImage.open(io.BytesIO(file_stream.read()))
            img.thumbnail((size, size), PILImage.LANCZOS)

            # Convert to WebP
            thumb_buffer = io.BytesIO()
            img.save(thumb_buffer, format='WEBP', quality=75)
            thumb_buffer.seek(0)

            # Cache the thumbnail in MinIO
            try:
                thumb_bytes = thumb_buffer.getvalue()
                minio_storage_provider.upload_file(
                    object_name=thumb_object,
                    data_stream=io.BytesIO(thumb_bytes),
                    content_type="image/webp",
                    bucket_name=bucket_name,
                )
            except Exception:
                pass  # Cache failure is non-fatal

            thumb_buffer.seek(0)
            return Stream(
                content=thumb_buffer,
                media_type="image/webp",
                headers={"Cache-Control": "public, max-age=86400"},
            )
        except ImportError:
            # Pillow not installed — fall back to full image
            return self.download_file(file_path)
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="An error occurred while generating thumbnail"),
                status_code=500,
            )
