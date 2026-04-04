"""
CSV controller for saving and downloading CSV data via MinIO storage.
"""
import csv
import io

from litestar import Response
from litestar.handlers import get, post
from litestar.params import Body
from litestar.controller import Controller
from litestar.response import Stream

from gemini.rest_api.models import RESTAPIError
from gemini.rest_api.controllers.files import minio_storage_provider, minio_storage_config

from pydantic import BaseModel
from typing import Optional, List


class CsvSaveRequest(BaseModel):
    file_path: str
    headers: List[str]
    rows: List[List[str]]
    bucket_name: Optional[str] = None


class CsvController(Controller):

    @post(path="/save", sync_to_thread=True)
    def save_csv(self, data: CsvSaveRequest) -> dict:
        """Save CSV data to MinIO storage."""
        try:
            bucket = data.bucket_name or minio_storage_config.bucket_name
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(data.headers)
            writer.writerows(data.rows)
            content = output.getvalue().encode("utf-8")
            stream = io.BytesIO(content)
            minio_storage_provider.upload_file(
                bucket_name=bucket,
                object_name=data.file_path,
                data_stream=stream,
                content_type="text/csv",
            )
            return {"status": "ok", "file_path": data.file_path, "size": len(content)}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to save CSV"),
                status_code=500,
            )

    @get(path="/download/{file_path:path}", sync_to_thread=True)
    def download_csv(self, file_path: str) -> Stream:
        """Download a CSV file from MinIO storage."""
        try:
            bucket_name = file_path.split('/')[0]
            object_name = '/'.join(file_path.split('/')[1:])
            file_stream = minio_storage_provider.download_file_stream(
                object_name=object_name,
                bucket_name=bucket_name,
            )
            return Stream(
                content=file_stream.stream(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={object_name.split('/')[-1]}"},
            )
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to download CSV"),
                status_code=500,
            )
