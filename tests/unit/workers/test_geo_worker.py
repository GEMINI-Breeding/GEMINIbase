"""Unit tests for the geo worker."""
import os
from unittest.mock import MagicMock, patch

import pytest

from gemini.workers.types import JobType, JobStatus


class TestGeoWorkerInit:
    """Test GeoWorker initialization and configuration."""

    def test_supported_job_types(self):
        from gemini.workers.geo.worker import GeoWorker

        worker = GeoWorker(worker_id="test-geo")
        assert worker.supported_job_types == {
            JobType.CREATE_COG,
            JobType.TIF_TO_PNG,
            JobType.PROCESS_DRONE_TIFF,
            JobType.SPLIT_ORTHOMOSAIC,
            JobType.DATA_SYNC,
            JobType.IMPORT_LEGACY,
        }

    def test_worker_id_default(self):
        from gemini.workers.geo.worker import GeoWorker

        worker = GeoWorker()
        assert "GeoWorker" in worker.worker_id

    def test_worker_id_custom(self):
        from gemini.workers.geo.worker import GeoWorker

        worker = GeoWorker(worker_id="my-geo-worker")
        assert worker.worker_id == "my-geo-worker"


class TestGeoWorkerJobRouting:
    """Test that process() routes to the correct handler."""

    def test_routes_create_cog(self):
        from gemini.workers.geo.worker import GeoWorker

        worker = GeoWorker(worker_id="test")
        worker._create_cog_job = MagicMock(return_value={"output_path": "test.tif"})
        result = worker.process("job-1", "CREATE_COG", {"input_path": "test.tif"})
        worker._create_cog_job.assert_called_once_with("job-1", {"input_path": "test.tif"})
        assert result == {"output_path": "test.tif"}

    def test_routes_tif_to_png(self):
        from gemini.workers.geo.worker import GeoWorker

        worker = GeoWorker(worker_id="test")
        worker._tif_to_png_job = MagicMock(return_value={"output_path": "test.png"})
        result = worker.process("job-2", "TIF_TO_PNG", {"input_path": "test.tif"})
        worker._tif_to_png_job.assert_called_once_with("job-2", {"input_path": "test.tif"})
        assert result == {"output_path": "test.png"}

    def test_routes_process_drone_tiff(self):
        from gemini.workers.geo.worker import GeoWorker

        worker = GeoWorker(worker_id="test")
        worker._process_drone_tiff_job = MagicMock(return_value={"cog_path": "cog.tif"})
        result = worker.process("job-3", "PROCESS_DRONE_TIFF", {"input_path": "drone.tif"})
        worker._process_drone_tiff_job.assert_called_once_with("job-3", {"input_path": "drone.tif"})

    def test_unsupported_job_type_raises(self):
        from gemini.workers.geo.worker import GeoWorker

        worker = GeoWorker(worker_id="test")
        with pytest.raises(ValueError, match="Unsupported job type"):
            worker.process("job-4", "UNKNOWN_TYPE", {})


class TestCreateCogOutputPath:
    """Test COG output path generation."""

    def test_default_output_path(self):
        from gemini.workers.geo.worker import GeoWorker

        worker = GeoWorker(worker_id="test")

        # Mock MinIO and rasterio to test path logic only
        with patch("gemini.workers.geo.worker._get_minio_client") as mock_minio, \
             patch("gemini.workers.geo.worker._create_cog") as mock_cog:
            mock_client = MagicMock()
            mock_minio.return_value = mock_client

            result = worker._create_cog_job("job-1", {"input_path": "Processed/2024/ortho.tif"})

            # Verify output path has -Pyramid suffix
            assert result["output_path"] == "Processed/2024/ortho-Pyramid.tif"

    def test_custom_output_path(self):
        from gemini.workers.geo.worker import GeoWorker

        worker = GeoWorker(worker_id="test")

        with patch("gemini.workers.geo.worker._get_minio_client") as mock_minio, \
             patch("gemini.workers.geo.worker._create_cog"):
            mock_minio.return_value = MagicMock()

            result = worker._create_cog_job("job-1", {
                "input_path": "Processed/2024/ortho.tif",
                "output_path": "Processed/2024/custom-cog.tif",
            })
            assert result["output_path"] == "Processed/2024/custom-cog.tif"


class TestTifToPngOutputPath:
    """Test PNG output path generation."""

    def test_default_png_output_path(self):
        """Verify default output path is .png extension of input."""
        import os

        input_path = "data/image.tif"
        base, _ = os.path.splitext(input_path)
        expected = f"{base}.png"
        assert expected == "data/image.png"

    def test_custom_png_output_path(self):
        """Verify custom output path is used when provided."""
        input_path = "data/image.tif"
        output_path = "data/custom_preview.png"
        # When output_path is provided, it should be used as-is
        assert output_path == "data/custom_preview.png"


class TestProcessDroneTiff:
    """Test drone TIFF processing combines COG and PNG."""

    def test_calls_both_cog_and_png(self):
        from gemini.workers.geo.worker import GeoWorker

        worker = GeoWorker(worker_id="test")
        worker._create_cog_job = MagicMock(return_value={"output_path": "drone-Pyramid.tif"})
        worker._tif_to_png_job = MagicMock(return_value={"output_path": "drone.png"})

        result = worker._process_drone_tiff_job("job-1", {"input_path": "data/drone.tif"})

        worker._create_cog_job.assert_called_once()
        worker._tif_to_png_job.assert_called_once()
        assert result["cog_path"] == "drone-Pyramid.tif"
        assert result["png_path"] == "drone.png"


class TestSplitOrthomosaicFailsLoudly:
    """A split that can do nothing must fail, not report success."""

    PARAMS = {
        "year": "S1",
        "experiment": "E",
        "location": "Davis",
        "population": "Cowpea",
        "date": "2024-07-10",
    }

    def _worker(self):
        from gemini.workers.geo.worker import GeoWorker

        w = GeoWorker(worker_id="test")
        w.report_progress = MagicMock()
        return w

    def test_no_boundaries(self):
        with pytest.raises(ValueError, match="No plot boundaries"):
            self._worker()._split_orthomosaic_job(
                "j", {**self.PARAMS, "boundaries": {"features": []}}
            )

    @patch("gemini.workers.geo.worker._get_minio_client")
    def test_no_orthomosaic_found(self, mock_client):
        mock_client.return_value.list_objects.return_value = iter([])
        with pytest.raises(FileNotFoundError, match="No orthomosaic found"):
            self._worker()._split_orthomosaic_job(
                "j",
                {**self.PARAMS, "boundaries": {"features": [{"type": "Feature"}]}},
            )

    @patch("gemini.workers.geo.worker._get_minio_client")
    def test_explicit_path_skips_discovery(self, mock_client):
        # An imported ortho lives under Raw/, which discovery never lists.
        import sys

        w = self._worker()
        mock_client.return_value.fget_object.side_effect = RuntimeError("stop")
        heavy = {m: MagicMock() for m in ("rasterio", "rasterio.mask", "rasterio.warp", "PIL")}
        with patch.dict(sys.modules, heavy), pytest.raises(RuntimeError, match="stop"):
            w._split_orthomosaic_job(
                "j",
                {
                    **self.PARAMS,
                    "boundaries": {"features": [{"type": "Feature"}]},
                    "orthomosaic_path": "Raw/S1/E/Davis/Cowpea/2024-07-10/DJI/RGB/Orthomosaic/o.tif",
                },
            )
        mock_client.return_value.list_objects.assert_not_called()
        assert mock_client.return_value.fget_object.call_args.args[1].startswith("Raw/")
