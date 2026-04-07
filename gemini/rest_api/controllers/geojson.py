"""
GeoJSON controller for loading and saving GeoJSON data via MinIO storage.
"""
import json

from litestar import Response
from litestar.handlers import post
from litestar.controller import Controller

from gemini.rest_api.models import RESTAPIError
from gemini.rest_api.controllers.files import minio_storage_provider, minio_storage_config

from pydantic import BaseModel
from typing import Optional


class GeoJsonLoadRequest(BaseModel):
    file_path: str
    bucket_name: Optional[str] = None


class GeoJsonSaveRequest(BaseModel):
    file_path: str
    geojson: dict
    bucket_name: Optional[str] = None


class GeoJsonController(Controller):

    @post(path="/load", sync_to_thread=True)
    def load_geojson(self, data: GeoJsonLoadRequest) -> dict:
        """Load a GeoJSON file from MinIO and return its contents."""
        try:
            bucket = data.bucket_name or minio_storage_config.bucket_name
            if not minio_storage_provider.file_exists(
                object_name=data.file_path, bucket_name=bucket
            ):
                return Response(
                    content=RESTAPIError(
                        error="Not found",
                        error_description=f"GeoJSON file {data.file_path} does not exist",
                    ),
                    status_code=404,
                )
            stream = minio_storage_provider.download_file_stream(
                object_name=data.file_path,
                bucket_name=bucket,
            )
            content = stream.read().decode("utf-8")
            stream.close()
            stream.release_conn()
            return json.loads(content)
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to load GeoJSON"),
                status_code=500,
            )

    @post(path="/save", sync_to_thread=True)
    def save_geojson(self, data: GeoJsonSaveRequest) -> dict:
        """Save GeoJSON data to MinIO storage."""
        try:
            import io
            bucket = data.bucket_name or minio_storage_config.bucket_name
            content = json.dumps(data.geojson, indent=2).encode("utf-8")
            stream = io.BytesIO(content)
            minio_storage_provider.upload_file(
                bucket_name=bucket,
                object_name=data.file_path,
                data_stream=stream,
                content_type="application/geo+json",
            )
            return {"status": "ok", "file_path": data.file_path, "size": len(content)}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to save GeoJSON"),
                status_code=500,
            )
