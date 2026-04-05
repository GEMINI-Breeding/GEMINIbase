"""Unit tests for the FLIR binary extraction worker."""
from unittest.mock import MagicMock, patch, call

import pytest

from gemini.workers.types import JobType


class TestFlirWorkerInit:
    """Test FlirWorker initialization."""

    def test_supported_job_types(self):
        from gemini.workers.flir.worker import FlirWorker

        worker = FlirWorker(worker_id="test-flir")
        assert worker.supported_job_types == {JobType.EXTRACT_BINARY}

    def test_worker_id_default(self):
        from gemini.workers.flir.worker import FlirWorker

        worker = FlirWorker()
        assert "FlirWorker" in worker.worker_id

    def test_worker_id_custom(self):
        from gemini.workers.flir.worker import FlirWorker

        worker = FlirWorker(worker_id="my-flir-worker")
        assert worker.worker_id == "my-flir-worker"


class TestFlirWorkerJobRouting:
    """Test that process() routes correctly."""

    def test_routes_extract_binary(self):
        from gemini.workers.flir.worker import FlirWorker

        worker = FlirWorker(worker_id="test")
        worker._extract_binary_job = MagicMock(return_value={"status": "completed"})
        result = worker.process("job-1", "EXTRACT_BINARY", {"files": ["a.bin"], "localDirPath": "/path"})
        worker._extract_binary_job.assert_called_once_with("job-1", {"files": ["a.bin"], "localDirPath": "/path"})

    def test_unsupported_job_type_raises(self):
        from gemini.workers.flir.worker import FlirWorker

        worker = FlirWorker(worker_id="test")
        with pytest.raises(ValueError, match="Unsupported job type"):
            worker.process("job-1", "UNKNOWN", {})


class TestFlirWorkerValidation:
    """Test parameter validation."""

    def test_missing_files_raises(self):
        from gemini.workers.flir.worker import FlirWorker

        worker = FlirWorker(worker_id="test")
        with pytest.raises(ValueError, match="Missing required parameters"):
            worker._extract_binary_job("job-1", {"localDirPath": "/path"})

    def test_missing_dir_path_raises(self):
        from gemini.workers.flir.worker import FlirWorker

        worker = FlirWorker(worker_id="test")
        with pytest.raises(ValueError, match="Missing required parameters"):
            worker._extract_binary_job("job-1", {"files": ["a.bin"]})

    def test_empty_files_raises(self):
        from gemini.workers.flir.worker import FlirWorker

        worker = FlirWorker(worker_id="test")
        with pytest.raises(ValueError, match="Missing required parameters"):
            worker._extract_binary_job("job-1", {"files": [], "localDirPath": "/path"})

    def test_no_bin_files_returns_skipped(self):
        from gemini.workers.flir.worker import FlirWorker

        worker = FlirWorker(worker_id="test")
        with patch("gemini.workers.flir.worker._get_minio_client"):
            result = worker._extract_binary_job("job-1", {
                "files": ["readme.txt", "photo.jpg"],
                "localDirPath": "/path",
            })
        assert result["status"] == "skipped"


class TestFlirWorkerTimestampSorting:
    """Test .bin file sorting by timestamp."""

    def test_extract_timestamp(self):
        from gemini.workers.flir.worker import _extract_timestamp

        assert _extract_timestamp("2024_01_15_12_30_45_001.bin") == "2024_01_15_12_30_45_001"
        assert _extract_timestamp("no_match.bin") == "no_match.bin"

    def test_bin_files_sorted_by_timestamp(self):
        from gemini.workers.flir.worker import FlirWorker, _extract_timestamp

        files = [
            "2024_01_15_12_30_45_003.bin",
            "2024_01_15_12_30_45_001.bin",
            "readme.txt",
            "2024_01_15_12_30_45_002.bin",
        ]
        bin_files = sorted(
            [f for f in files if f.endswith(".bin")],
            key=_extract_timestamp,
        )
        assert bin_files == [
            "2024_01_15_12_30_45_001.bin",
            "2024_01_15_12_30_45_002.bin",
            "2024_01_15_12_30_45_003.bin",
        ]


class TestFlirWorkerExtractionFlow:
    """Test the extraction job flow with mocked MinIO and extraction."""

    @pytest.fixture(autouse=True)
    def _mock_bin_to_images(self):
        """Mock the bin_to_images module which requires farm_ng/torch."""
        import sys
        import types

        self.mock_bin_module = types.ModuleType("gemini.workers.flir.bin_to_images")
        self.mock_bin_module.extract_binary = MagicMock()
        sys.modules["gemini.workers.flir.bin_to_images"] = self.mock_bin_module
        yield
        sys.modules.pop("gemini.workers.flir.bin_to_images", None)

    @patch("gemini.workers.flir.worker._get_minio_client")
    @patch("gemini.workers.flir.worker.FlirWorker.report_progress")
    @patch("gemini.workers.flir.worker.FlirWorker.is_cancelled", return_value=False)
    def test_full_flow_downloads_extracts_uploads(self, mock_cancelled, mock_progress, mock_minio):
        import os
        import tempfile
        from gemini.workers.flir.worker import FlirWorker

        mock_client = MagicMock()
        mock_minio.return_value = mock_client

        worker = FlirWorker(worker_id="test")

        with tempfile.TemporaryDirectory() as real_tmpdir:
            # Create simulated extraction output structure
            output_dir = os.path.join(real_tmpdir, "output")
            os.makedirs(os.path.join(output_dir, "RGB", "Metadata"))
            os.makedirs(os.path.join(output_dir, "RGB", "Images", "top"))
            for f in ["RGB/Metadata/msgs_synced.csv", "RGB/Metadata/gps_pvt.csv",
                       "RGB/Images/top/rgb-001.jpg", "RGB/Images/top/rgb-002.jpg"]:
                with open(os.path.join(output_dir, f), "w") as fh:
                    fh.write("test")

            def mock_extract(file_paths, out_path):
                """Simulate extraction by copying pre-created files into out_path."""
                import shutil
                # Copy our pre-created structure into the actual output_dir used by the worker
                for item in os.listdir(output_dir):
                    src = os.path.join(output_dir, item)
                    dst = os.path.join(str(out_path), item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)

            self.mock_bin_module.extract_binary.side_effect = mock_extract

            result = worker._extract_binary_job("job-1", {
                "files": ["2024_01_15_001.bin", "readme.txt"],
                "localDirPath": "2024/Exp1/Field1/Pop1/2024-01-15/Amiga/OAK/Amiga",
            })

        # Verify MinIO download was called for the .bin file
        mock_client.fget_object.assert_called_once()
        download_call = mock_client.fget_object.call_args
        assert download_call[0][1] == "2024/Exp1/Field1/Pop1/2024-01-15/Amiga/OAK/Amiga/2024_01_15_001.bin"

        # Verify extract_binary was called
        self.mock_bin_module.extract_binary.assert_called_once()

        # Verify files were uploaded back
        assert mock_client.fput_object.call_count == 4  # 2 CSVs + 2 JPGs

        # Verify .bin cleanup
        mock_client.remove_object.assert_called_once()

        assert result["status"] == "completed"
        assert result["bin_files_processed"] == 1
        assert result["extracted_files"] == 4

    @patch("gemini.workers.flir.worker._get_minio_client")
    @patch("gemini.workers.flir.worker.FlirWorker.report_progress")
    @patch("gemini.workers.flir.worker.FlirWorker.is_cancelled")
    def test_cancellation_during_download(self, mock_cancelled, mock_progress, mock_minio):
        from gemini.workers.flir.worker import FlirWorker

        # Cancel after first progress report
        mock_cancelled.side_effect = [True]
        mock_minio.return_value = MagicMock()

        worker = FlirWorker(worker_id="test")
        result = worker._extract_binary_job("job-1", {
            "files": ["2024_01_15_001.bin"],
            "localDirPath": "path/to/dir",
        })
        assert result["status"] == "cancelled"


class TestFlirWorkerOutputPaths:
    """Test that output files are placed correctly relative to input dir."""

    def test_output_placed_in_parent_of_amiga_dir(self):
        """Output (RGB/, Disparity/) should be siblings of the Amiga/ input dir."""
        from pathlib import Path

        dir_path = "2024/Exp1/Field1/Pop1/2024-01-15/Amiga/OAK/Amiga"
        parent_dir = str(Path(dir_path).parent)
        assert parent_dir == "2024/Exp1/Field1/Pop1/2024-01-15/Amiga/OAK"

        # An output file like "RGB/Metadata/msgs_synced.csv" becomes:
        relative = "RGB/Metadata/msgs_synced.csv"
        object_name = f"{parent_dir}/{relative}"
        assert object_name == "2024/Exp1/Field1/Pop1/2024-01-15/Amiga/OAK/RGB/Metadata/msgs_synced.csv"
