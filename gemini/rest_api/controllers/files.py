import io
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
    AbortUploadRequest,
    PresignedUrlResponse,
)

from gemini.manager import GEMINIManager, GEMINIComponentType
from gemini.storage.providers.minio_storage import MinioStorageProvider
from gemini.storage.config.storage_config import MinioStorageConfig

from typing import Annotated, List

# In-memory session state for in-flight S3 multipart uploads. One entry per
# file_identifier, populated when the first chunk arrives and torn down on
# completion or abort.
#
#   {
#     file_identifier: {
#       "upload_id":   str,                 # opaque MinIO multipart id
#       "bucket_name": str,
#       "object_name": str,
#       "parts":       dict[int, str],      # part_number (1-indexed) -> etag
#       "total":       int,                 # expected total_chunks
#     }
#   }
#
# Single-process safe (Uvicorn runs --workers=1). If we ever scale horizontally
# this needs to move to Redis.
_chunk_uploads: dict[str, dict] = {}


def _record_experiment_file(
    experiment_id: str,
    bucket: str,
    object_name: str,
) -> None:
    """Insert (or no-op-update) the experiment_files row for a finalised
    chunked upload. Idempotent on (bucket, object_name) so a retried
    completion request can't 23505 the upload."""
    import logging

    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from gemini.db.core.base import db_engine
    from gemini.db.models.experiment_files import ExperimentFileModel
    from gemini.db.models.experiments import ExperimentModel

    logger = logging.getLogger(__name__)
    try:
        with db_engine.get_session() as session:
            # Validate the experiment exists. Without this, a typo'd /
            # spoofed experiment_id silently produces an orphan row that
            # the cascade can't reach. Better to log + skip than insert
            # garbage.
            exists = session.execute(
                select(ExperimentModel.id).where(
                    ExperimentModel.id == experiment_id
                )
            ).scalar_one_or_none()
            if exists is None:
                logger.warning(
                    "experiment_files: refusing to record %s for unknown "
                    "experiment_id %s", object_name, experiment_id,
                )
                return
            stmt = pg_insert(ExperimentFileModel.__table__).values(
                experiment_id=experiment_id,
                bucket=bucket,
                object_name=object_name,
            ).on_conflict_do_nothing(
                constraint="experiment_files_unique_object",
            )
            session.execute(stmt)
    except Exception as exc:
        logger.warning(
            "experiment_files: failed to record (%s, %s): %s",
            bucket, object_name, exc,
        )

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
            # Single MinIO list call returns object_name + size +
            # last_modified + etag inline. Content type isn't in the listing
            # response, so it's reported as unknown — callers that need it
            # can fetch the object directly.
            entries = minio_storage_provider.list_files_with_metadata(
                bucket_name=bucket_name,
                prefix=prefix,
            )
            return [
                FileMetadata(
                    bucket_name=entry["bucket_name"],
                    object_name=entry["object_name"],
                    size=entry["size"],
                    last_modified=entry["last_modified"],
                    content_type="application/octet-stream",
                    etag=entry["etag"],
                )
                for entry in entries
            ]
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
        Delete a single file from MinIO.

        This endpoint deliberately refuses prefix (folder) deletion —
        MinIO "folders" that correspond to datasets / experiments /
        sensors / etc. are owned by DB entities, and wiping the files
        without cleaning up the DB rows leaves dangling ``record_file``
        references. Delete via the entity's DELETE endpoint instead;
        that cascades to MinIO safely.
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

            file_exists = minio_storage_provider.file_exists(
                object_name=object_name,
                bucket_name=bucket_name
            )
            if not file_exists:
                return Response(
                    content=RESTAPIError(
                        error="Not found",
                        error_description=(
                            f"No file at {file_path}. Folder (prefix) deletion "
                            "is not allowed here — delete the owning entity "
                            "(dataset, experiment, sensor, …) instead."
                        ),
                    ),
                    status_code=404,
                )

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
            # After a successful MinIO delete, drop the matching
            # experiment_files row so the DB doesn't keep a dangling
            # pointer at the now-gone object. The chunked-upload finaliser
            # at `_record_experiment_file` is the only writer of these
            # rows; it keys on (bucket, object_name) which is also our
            # unique constraint — so the DELETE is at-most-one-row.
            try:
                from gemini.db.core.base import db_engine
                from gemini.db.models.experiment_files import ExperimentFileModel
                with db_engine.get_session() as session:
                    session.execute(
                        ExperimentFileModel.__table__.delete().where(
                            (ExperimentFileModel.bucket == bucket_name)
                            & (ExperimentFileModel.object_name == object_name)
                        )
                    )
                    session.commit()
            except Exception as exc:
                # Logged-warning, not fatal: the MinIO object is already
                # gone, so a subsequent Experiment.delete() that tries to
                # remove this object via the row-targeted sweep will
                # see a missing-object warning rather than a zombie row.
                import logging
                logging.getLogger(__name__).warning(
                    "experiment_files row sweep for %s/%s failed: %s",
                    bucket_name, object_name, exc,
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
        """Receive a single chunk and stream it directly into a MinIO multipart part.

        The first chunk for a given file_identifier initiates the multipart
        upload; each chunk is uploaded as one S3 part (1-indexed); when the
        recorded part count equals total_chunks we ask MinIO to assemble.
        No local-disk buffering on the API container.
        """
        file_id = data.file_identifier
        try:
            chunk_idx = data.chunk_index
            total = data.total_chunks
            part_number = chunk_idx + 1  # S3 parts are 1-indexed
            bucket_name = data.bucket_name or minio_storage_config.bucket_name

            session = _chunk_uploads.get(file_id)
            if session is None:
                upload_id = minio_storage_provider.create_multipart_upload(
                    object_name=data.object_name,
                    bucket_name=bucket_name,
                )
                session = {
                    "upload_id": upload_id,
                    "bucket_name": bucket_name,
                    "object_name": data.object_name,
                    "parts": {},
                    "total": total,
                }
                _chunk_uploads[file_id] = session

            # Idempotent re-send of an already-uploaded part: skip the upload but
            # still report current progress.
            if part_number not in session["parts"]:
                chunk_bytes = data.file_chunk.file.read()
                etag = minio_storage_provider.upload_part(
                    object_name=session["object_name"],
                    upload_id=session["upload_id"],
                    part_number=part_number,
                    data=chunk_bytes,
                    bucket_name=session["bucket_name"],
                )
                session["parts"][part_number] = etag

            uploaded_part_numbers = sorted(session["parts"].keys())

            if len(uploaded_part_numbers) == total:
                minio_storage_provider.complete_multipart_upload(
                    object_name=session["object_name"],
                    upload_id=session["upload_id"],
                    parts=list(session["parts"].items()),
                    bucket_name=session["bucket_name"],
                )
                # Phase 9j: write the authoritative pointer row so the
                # experiment-delete cascade can sweep this object by row
                # rather than guessing the path layout. Idempotent on
                # (bucket, object_name) so a retried-completion (e.g.
                # network error on the very last chunk's response) is
                # safe. Failure here is logged but not fatal — the
                # MinIO write already succeeded and we'd rather have an
                # untracked file than fail an upload the user already
                # paid for.
                if data.experiment_id:
                    _record_experiment_file(
                        experiment_id=data.experiment_id,
                        bucket=session["bucket_name"],
                        object_name=session["object_name"],
                    )
                del _chunk_uploads[file_id]
                return ChunkStatusResponse(
                    file_identifier=file_id,
                    uploaded_part_numbers=uploaded_part_numbers,
                    total_chunks=total,
                    complete=True,
                )

            return ChunkStatusResponse(
                file_identifier=file_id,
                uploaded_part_numbers=uploaded_part_numbers,
                total_chunks=total,
                complete=False,
            )
        except Exception as e:
            # Best-effort abort so we don't leak an in-progress multipart upload.
            session = _chunk_uploads.pop(file_id, None)
            if session is not None:
                try:
                    minio_storage_provider.abort_multipart_upload(
                        object_name=session["object_name"],
                        upload_id=session["upload_id"],
                        bucket_name=session["bucket_name"],
                    )
                except Exception:
                    pass
            return Response(
                content=RESTAPIError(error=str(e), error_description="Chunk upload failed"),
                status_code=500,
            )

    @post(path="/check_uploaded_chunks", sync_to_thread=True)
    def check_uploaded_chunks(
        self,
        data: dict,
    ) -> ChunkStatusResponse:
        """Report which part numbers MinIO has stored for this file_identifier.

        If the in-memory session is gone (e.g. API container restarted), we
        cannot recover the upload_id, so resume from MinIO is not possible and
        we report nothing uploaded — the client will start fresh.
        """
        file_id = data.get("file_identifier", "")
        total = int(data.get("total_chunks", 0) or 0)
        session = _chunk_uploads.get(file_id)
        uploaded_part_numbers = sorted(session["parts"].keys()) if session else []
        return ChunkStatusResponse(
            file_identifier=file_id,
            uploaded_part_numbers=uploaded_part_numbers,
            total_chunks=total,
            complete=False,
        )

    @post(path="/abort_upload", sync_to_thread=True)
    def abort_upload(
        self,
        data: AbortUploadRequest,
    ) -> dict:
        """Cancel an in-progress multipart upload and free its session state."""
        session = _chunk_uploads.pop(data.file_identifier, None)
        if session is not None:
            try:
                minio_storage_provider.abort_multipart_upload(
                    object_name=session["object_name"],
                    upload_id=session["upload_id"],
                    bucket_name=session["bucket_name"],
                )
            except Exception:
                pass
        return {"status": "ok", "file_identifier": data.file_identifier}

    @post(path="/clear_upload_cache", sync_to_thread=True)
    def clear_upload_cache(
        self,
        data: dict,
    ) -> dict:
        """Backwards-compatible alias for /abort_upload."""
        file_id = data.get("file_identifier", "")
        session = _chunk_uploads.pop(file_id, None)
        if session is not None:
            try:
                minio_storage_provider.abort_multipart_upload(
                    object_name=session["object_name"],
                    upload_id=session["upload_id"],
                    bucket_name=session["bucket_name"],
                )
            except Exception:
                pass
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
    def list_dirs_nested(self) -> list:
        """Flat list of every file under Raw/ with metadata. The frontend
        groups these into a tree."""
        try:
            bucket = minio_storage_config.bucket_name
            client = minio_storage_provider.client
            objects = client.list_objects(
                bucket_name=bucket, prefix="Raw/", recursive=True
            )
            files = []
            for obj in objects:
                if obj.is_dir:
                    continue
                files.append({
                    'bucket_name': bucket,
                    'object_name': obj.object_name,
                    'size': obj.size or 0,
                    'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                    'content_type': obj.content_type,
                })
            return files
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to list nested files"),
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
