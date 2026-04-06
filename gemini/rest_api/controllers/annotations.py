"""
Annotations controller for managing training labels and CVAT integration.

Provides endpoints for checking, uploading, and managing YOLO-format
annotation files stored in MinIO.
"""
import io

from litestar import Response
from litestar.handlers import post
from litestar.params import Body
from litestar.controller import Controller
from litestar.enums import RequestEncodingType
from litestar.datastructures import UploadFile

from gemini.rest_api.models import RESTAPIError
from gemini.rest_api.controllers.files import minio_storage_provider, minio_storage_config

from pydantic import BaseModel
from typing import List, Optional, Annotated


def _bucket():
    return minio_storage_config.bucket_name


class CheckLabelsRequest(BaseModel):
    dirPath: str
    fileList: List[str]


class UploadLabelsRequest(BaseModel):
    files: UploadFile
    dirPath: str


class AnnotationsController(Controller):

    @post(path="/check_labels", sync_to_thread=True)
    def check_existing_labels(self, data: CheckLabelsRequest) -> List[str]:
        """Check which label files already exist on the server.

        Returns the list of files that do NOT exist (need to be uploaded).
        """
        try:
            existing = set()
            try:
                items = minio_storage_provider.list_files(
                    bucket_name=_bucket(),
                    prefix=data.dirPath,
                )
                for item in items:
                    filename = item.object_name.split("/")[-1]
                    existing.add(filename)
            except Exception:
                pass

            # Return files that don't exist yet
            return [f for f in data.fileList if f not in existing]
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to check labels"),
                status_code=500,
            )

    @post(path="/upload_labels", sync_to_thread=True)
    def upload_trait_labels(
        self,
        data: Annotated[UploadLabelsRequest, Body(media_type=RequestEncodingType.MULTI_PART)],
    ) -> dict:
        """Upload YOLO-format label files to MinIO."""
        try:
            file_obj = data.files
            filename = file_obj.filename or "unknown"
            dir_path = data.dirPath

            # Ensure directory path format
            if not dir_path.endswith("/"):
                dir_path += "/"

            object_name = f"{dir_path}{filename}"
            file_stream = file_obj.file

            minio_storage_provider.upload_file(
                bucket_name=_bucket(),
                object_name=object_name,
                data_stream=file_stream,
                content_type=file_obj.content_type or "application/octet-stream",
            )

            return {"status": "ok", "uploaded": filename, "path": object_name}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to upload labels"),
                status_code=500,
            )

    @post(path="/start_cvat", sync_to_thread=True)
    def start_cvat(self) -> dict:
        """Launch CVAT container for annotation.

        Note: CVAT Docker integration requires Docker socket access.
        In framework mode, CVAT should be deployed as a separate service.
        """
        try:
            # In framework mode, CVAT is expected to be a separate Docker service
            # Return the URL for the CVAT instance
            return {
                "status": "CVAT should be accessible at http://localhost:8080/",
                "message": "In framework mode, start CVAT via docker compose separately.",
            }
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to start CVAT"),
                status_code=500,
            )
