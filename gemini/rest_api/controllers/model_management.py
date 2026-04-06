"""
Model management controller for training model discovery and metadata.

Scans MinIO for model weight files and training logs, providing the same
functionality as Flask's get_model_info, get_locate_info, best_locate_file,
best_model_file, and done_training endpoints.
"""
import json

from litestar import Response
from litestar.handlers import post
from litestar.controller import Controller

from gemini.rest_api.models import RESTAPIError
from gemini.rest_api.controllers.files import minio_storage_provider, minio_storage_config

from pydantic import BaseModel
from typing import Any, Optional, List


def _bucket():
    return minio_storage_config.bucket_name


def _read_json(path: str) -> Optional[dict]:
    """Read a JSON file from MinIO, return None on failure."""
    try:
        stream = minio_storage_provider.download_file_stream(
            object_name=path, bucket_name=_bucket()
        )
        content = stream.read().decode("utf-8")
        stream.close()
        stream.release_conn()
        return json.loads(content)
    except Exception:
        return None


def _list_objects(prefix: str) -> list:
    """List objects in MinIO under a prefix."""
    try:
        items = minio_storage_provider.list_files(
            bucket_name=_bucket(), prefix=prefix
        )
        return [item.object_name for item in items]
    except Exception:
        return []


class ModelManagementController(Controller):

    @post(path="/info", sync_to_thread=True)
    def get_model_info(self, data: Any) -> Any:
        """Get model metadata for a set of training runs.

        Input: dict of {run_path: run_data, ...} from check_runs output.
        Returns: list of model info dicts with batch, epochs, imgsz, map, etc.
        """
        try:
            if not isinstance(data, dict):
                return []

            results = []
            for run_path, run_data in data.items():
                # Try to read logs.yaml or similar metadata
                logs = _read_json(f"{run_path}/logs.yaml") or _read_json(f"{run_path}/results.json")
                info = {
                    "path": run_path,
                    "run_id": run_path.split("/")[-1] if "/" in str(run_path) else run_path,
                    "batch": -1,
                    "epochs": 0,
                    "imgsz": 640,
                    "map": 0.0,
                }
                if logs:
                    info.update({
                        "batch": logs.get("batch", -1),
                        "epochs": logs.get("epochs", 0),
                        "imgsz": logs.get("imgsz", 640),
                        "map": logs.get("map", logs.get("mAP50", 0.0)),
                    })

                # Check for weight files
                weights = _list_objects(f"{run_path}/weights/")
                info["has_best"] = any("best.pt" in w for w in weights)
                info["has_last"] = any("last.pt" in w for w in weights)

                results.append(info)

            return results
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to get model info"),
                status_code=500,
            )

    @post(path="/locate_info", sync_to_thread=True)
    def get_locate_info(self, data: Any) -> Any:
        """Get locate run metadata.

        Input: dict of {run_path: run_data, ...} from check_runs output.
        Returns: list of locate info dicts.
        """
        try:
            if not isinstance(data, dict):
                return []

            results = []
            for run_path, run_data in data.items():
                info = {
                    "path": run_path,
                    "run_id": run_path.split("/")[-1] if "/" in str(run_path) else run_path,
                }
                # Try to read any metadata
                logs = _read_json(f"{run_path}/results.json") or _read_json(f"{run_path}/logs.yaml")
                if logs:
                    info.update(logs)

                results.append(info)

            return results
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to get locate info"),
                status_code=500,
            )

    @post(path="/best_locate", sync_to_thread=True)
    def best_locate_file(self, data: Any) -> Any:
        """Find the best locate model file among a list of paths.

        Input: list of locate file paths.
        Returns: dict with best locate file path.
        """
        try:
            if not isinstance(data, list) or not data:
                return {"best": None}

            # Find the path with best.pt weights
            for path in data:
                weights = _list_objects(f"{path}/weights/")
                if any("best.pt" in w for w in weights):
                    best_path = next(w for w in weights if "best.pt" in w)
                    return {"best": best_path}

            # Fallback: return the first path that has any weights
            for path in data:
                weights = _list_objects(f"{path}/weights/")
                if weights:
                    return {"best": weights[0]}

            return {"best": data[0] if data else None}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to find best locate file"),
                status_code=500,
            )

    @post(path="/best_model", sync_to_thread=True)
    def best_model_file(self, data: Any) -> Any:
        """Find the best training model file among a list of paths.

        Input: list of model file paths.
        Returns: dict with best model file path.
        """
        try:
            if not isinstance(data, list) or not data:
                return {"best": None}

            for path in data:
                weights = _list_objects(f"{path}/weights/")
                if any("best.pt" in w for w in weights):
                    best_path = next(w for w in weights if "best.pt" in w)
                    return {"best": best_path}

            for path in data:
                weights = _list_objects(f"{path}/weights/")
                if weights:
                    return {"best": weights[0]}

            return {"best": data[0] if data else None}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to find best model file"),
                status_code=500,
            )

    @post(path="/done", sync_to_thread=True)
    def done_training(self) -> dict:
        """Mark model training as complete. In framework mode, this is a no-op
        since job status is tracked via the jobs controller."""
        return {"status": "ok"}
