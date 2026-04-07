"""
Integration tests for the ODM worker.

Tests the full worker pipeline with a mock NodeODM HTTP server,
real PostgreSQL (jobs table), and real MinIO (file storage).

Requires: docker compose -f tests/docker-compose.test.yaml up -d
"""

import importlib
import io
import json
import os
import struct
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from uuid import uuid4

import pytest

# The root conftest replaces sys.modules["minio"] with a MagicMock so that
# unit tests can run without MinIO.  Integration tests need the *real* minio
# library, so restore it before any worker code is imported.
for _key in [k for k in sys.modules if k == "minio" or k.startswith("minio.")]:
    del sys.modules[_key]
import minio as _real_minio  # noqa: E402 — force real import
# Re-register so subsequent `from minio import Minio` gets the real one
sys.modules["minio"] = _real_minio

from tests.integration.conftest import (
    TEST_MINIO_HOST,
    TEST_MINIO_PORT,
)

pytestmark = pytest.mark.integration

BUCKET = os.environ.get("GEMINI_TEST_BUCKET", "gemini-test")

# Small valid TIFF (10x10 pixel, 3 bands, no geospatial data but enough to verify upload)
def _make_tiny_tiff():
    """Create a minimal valid TIFF file in memory."""
    # Minimal TIFF: header + IFD with width/height/bits tags
    # This is a simplified TIFF that most readers will accept
    width, height = 20, 20
    pixel_data = bytes([128, 64, 32] * width * height)  # RGB pixels

    # TIFF header (little-endian)
    header = struct.pack("<2sHI", b"II", 42, 8)  # byte order, magic, IFD offset

    # IFD entries
    ifd_entries = [
        (256, 3, 1, width),       # ImageWidth
        (257, 3, 1, height),      # ImageLength
        (258, 3, 3, 0),           # BitsPerSample (offset filled below)
        (259, 3, 1, 1),           # Compression = no compression
        (262, 3, 1, 2),           # PhotometricInterpretation = RGB
        (273, 4, 1, 0),           # StripOffsets (filled below)
        (277, 3, 1, 3),           # SamplesPerPixel
        (278, 3, 1, height),      # RowsPerStrip
        (279, 4, 1, len(pixel_data)),  # StripByteCounts
    ]

    num_entries = len(ifd_entries)
    ifd_size = 2 + num_entries * 12 + 4  # count + entries + next IFD pointer

    # Calculate offsets
    ifd_start = 8  # right after header
    after_ifd = ifd_start + ifd_size
    bits_offset = after_ifd
    pixel_offset = bits_offset + 6  # 3 x uint16 for BitsPerSample

    # Update entries with calculated offsets
    ifd_entries[2] = (258, 3, 3, bits_offset)   # BitsPerSample offset
    ifd_entries[5] = (273, 4, 1, pixel_offset)  # StripOffsets

    # Pack IFD
    ifd = struct.pack("<H", num_entries)
    for tag, type_, count, value in ifd_entries:
        ifd += struct.pack("<HHII", tag, type_, count, value)
    ifd += struct.pack("<I", 0)  # Next IFD pointer (none)

    # BitsPerSample values
    bits_data = struct.pack("<HHH", 8, 8, 8)

    return header + ifd + bits_data + pixel_data


class MockNodeODMHandler(BaseHTTPRequestHandler):
    """Mock NodeODM HTTP handler for testing."""

    # Class-level state shared across requests
    tasks = {}
    fail_next = False
    log_lines = ["[INFO] Starting OpenDroneMap", "[INFO] Processing 3 images"]

    def log_message(self, format, *args):
        pass  # Suppress request logs during tests

    def do_GET(self):
        if self.path == "/info":
            self._json_response({"version": "2.8.0", "taskQueueCount": 0})
            return

        # /task/{uuid}/info
        if "/info" in self.path:
            task_id = self.path.split("/task/")[1].split("/info")[0]
            task = self.tasks.get(task_id, {})
            if not task:
                self._json_response({"error": "not found"}, 404)
                return
            self._json_response(task)
            return

        # /task/{uuid}/output
        if "/output" in self.path:
            self._json_response(self.log_lines)
            return

        # /task/{uuid}/download/{asset}
        if "/download/" in self.path:
            asset = self.path.rsplit("/download/", 1)[-1]
            tiff_data = _make_tiny_tiff()
            if asset == "all.zip":
                # Worker expects a zip containing odm_orthophoto.tif
                import zipfile as _zf
                buf = io.BytesIO()
                with _zf.ZipFile(buf, "w") as zf:
                    zf.writestr("odm_orthophoto/odm_orthophoto.tif", tiff_data)
                zip_data = buf.getvalue()
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Length", str(len(zip_data)))
                self.end_headers()
                self.wfile.write(zip_data)
            else:
                self.send_response(200)
                self.send_header("Content-Type", "image/tiff")
                self.send_header("Content-Length", str(len(tiff_data)))
                self.end_headers()
                self.wfile.write(tiff_data)
            return

        self._json_response({"error": "not found"}, 404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))

        # /task/new
        if self.path == "/task/new":
            # Read and discard the multipart body
            if content_length > 0:
                self.rfile.read(content_length)

            task_id = str(uuid4())

            if self.fail_next:
                self.__class__.fail_next = False
                self.tasks[task_id] = {
                    "uuid": task_id,
                    "status": {"code": 30, "errorMessage": "ODM processing failed: test error"},
                    "progress": 0,
                    "processingTime": 0,
                    "imagesCount": 0,
                }
            else:
                self.tasks[task_id] = {
                    "uuid": task_id,
                    "status": {"code": 40},  # COMPLETED immediately
                    "progress": 100,
                    "processingTime": 1,
                    "imagesCount": 3,
                }

            self._json_response({"uuid": task_id})
            return

        # /task/cancel
        if self.path == "/task/cancel":
            body = self.rfile.read(content_length)
            data = json.loads(body) if body else {}
            task_id = data.get("uuid", "")
            if task_id in self.tasks:
                self.tasks[task_id]["status"] = {"code": 50}
            self._json_response({"success": True})
            return

        # /task/remove
        if self.path == "/task/remove":
            body = self.rfile.read(content_length)
            data = json.loads(body) if body else {}
            task_id = data.get("uuid", "")
            self.tasks.pop(task_id, None)
            self._json_response({"success": True})
            return

        self._json_response({"error": "not found"}, 404)

    def _json_response(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def mock_nodeodm():
    """Start a mock NodeODM HTTP server on a random port."""
    MockNodeODMHandler.tasks = {}
    MockNodeODMHandler.fail_next = False

    server = HTTPServer(("127.0.0.1", 0), MockNodeODMHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture(scope="module")
def minio_client():
    """Create a MinIO client for the test instance."""
    from minio import Minio

    client = Minio(
        f"{TEST_MINIO_HOST}:{TEST_MINIO_PORT}",
        access_key="gemini_test_user",
        secret_key="gemini_test_secret",
        secure=False,
    )
    # Ensure test bucket exists
    if not client.bucket_exists(BUCKET):
        client.make_bucket(BUCKET)
    yield client


@pytest.fixture(autouse=True)
def clean_mock_nodeodm():
    """Reset mock NodeODM state between tests."""
    MockNodeODMHandler.tasks = {}
    MockNodeODMHandler.fail_next = False
    yield


def _seed_test_images(client, prefix: str, count: int = 3):
    """Seed small JPEG files to MinIO under the given prefix."""
    from PIL import Image

    for i in range(count):
        img = Image.new("RGB", (64, 64), color=(i * 80, 100, 50))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        object_name = f"{prefix}test_image_{i:03d}.jpg"
        client.put_object(BUCKET, object_name, buf, len(buf.getvalue()))


def _cleanup_prefix(client, prefix: str):
    """Remove all objects under a MinIO prefix."""
    objects = list(client.list_objects(BUCKET, prefix=prefix, recursive=True))
    for obj in objects:
        client.remove_object(BUCKET, obj.object_name)


class TestNodeODMClient:
    """Test the NodeODM client against the mock server."""

    def test_info(self, mock_nodeodm):
        from gemini.workers.odm.nodeodm_client import NodeODMClient

        client = NodeODMClient(base_url=mock_nodeodm)
        info = client.info()
        assert info["version"] == "2.8.0"

    def test_is_healthy(self, mock_nodeodm):
        from gemini.workers.odm.nodeodm_client import NodeODMClient

        client = NodeODMClient(base_url=mock_nodeodm)
        assert client.is_healthy() is True

    def test_is_healthy_bad_url(self):
        from gemini.workers.odm.nodeodm_client import NodeODMClient

        client = NodeODMClient(base_url="http://127.0.0.1:1")
        assert client.is_healthy() is False

    def test_create_task(self, mock_nodeodm, tmp_path):
        from gemini.workers.odm.nodeodm_client import NodeODMClient

        client = NodeODMClient(base_url=mock_nodeodm)
        # Create dummy image files
        for i in range(2):
            (tmp_path / f"img_{i}.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 100)

        image_paths = [str(tmp_path / f"img_{i}.jpg") for i in range(2)]
        task_id = client.create_task(image_paths)
        assert task_id is not None
        assert len(task_id) == 36  # UUID format

    def test_get_task_info(self, mock_nodeodm, tmp_path):
        from gemini.workers.odm.nodeodm_client import NodeODMClient

        client = NodeODMClient(base_url=mock_nodeodm)
        (tmp_path / "img.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 100)
        task_id = client.create_task([str(tmp_path / "img.jpg")])

        info = client.get_task_info(task_id)
        assert info["uuid"] == task_id
        assert info["status"]["code"] == 40  # COMPLETED

    def test_get_task_output(self, mock_nodeodm, tmp_path):
        from gemini.workers.odm.nodeodm_client import NodeODMClient

        client = NodeODMClient(base_url=mock_nodeodm)
        (tmp_path / "img.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 100)
        task_id = client.create_task([str(tmp_path / "img.jpg")])

        output = client.get_task_output(task_id)
        assert isinstance(output, list)
        assert any("Starting OpenDroneMap" in line for line in output)

    def test_download_result(self, mock_nodeodm, tmp_path):
        from gemini.workers.odm.nodeodm_client import NodeODMClient

        client = NodeODMClient(base_url=mock_nodeodm)
        (tmp_path / "img.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 100)
        task_id = client.create_task([str(tmp_path / "img.jpg")])

        dest = str(tmp_path / "ortho.tif")
        client.download_result(task_id, "orthophoto.tif", dest)
        assert os.path.exists(dest)
        assert os.path.getsize(dest) > 0
        # Verify it starts with TIFF magic bytes
        with open(dest, "rb") as f:
            assert f.read(2) == b"II"  # little-endian TIFF

    def test_cancel_task(self, mock_nodeodm, tmp_path):
        from gemini.workers.odm.nodeodm_client import NodeODMClient

        client = NodeODMClient(base_url=mock_nodeodm)
        (tmp_path / "img.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 100)
        task_id = client.create_task([str(tmp_path / "img.jpg")])

        result = client.cancel_task(task_id)
        assert result["success"] is True

    def test_remove_task(self, mock_nodeodm, tmp_path):
        from gemini.workers.odm.nodeodm_client import NodeODMClient

        client = NodeODMClient(base_url=mock_nodeodm)
        (tmp_path / "img.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 100)
        task_id = client.create_task([str(tmp_path / "img.jpg")])

        result = client.remove_task(task_id)
        assert result["success"] is True


class TestOdmWorkerHelpers:
    """Test worker helper functions."""

    def test_build_image_prefix(self):
        from gemini.workers.odm.worker import _build_image_prefix

        params = {
            "year": "2024",
            "experiment": "test_exp",
            "location": "field_a",
            "population": "pop1",
            "date": "2024-06-15",
            "platform": "DJI",
            "sensor": "RGB",
        }
        prefix = _build_image_prefix(params)
        assert prefix == "2024/test_exp/field_a/pop1/2024-06-15/DJI/RGB/Images/"

    def test_build_output_prefix(self):
        from gemini.workers.odm.worker import _build_output_prefix

        params = {
            "year": "2024",
            "experiment": "test_exp",
            "location": "field_a",
            "population": "pop1",
            "date": "2024-06-15",
            "platform": "DJI",
            "sensor": "RGB",
        }
        prefix = _build_output_prefix(params)
        assert prefix == "Processed/2024/test_exp/field_a/pop1/2024-06-15/DJI/RGB/"

    def test_parse_custom_options_cli_style(self):
        from gemini.workers.odm.worker import _parse_custom_options

        opts = _parse_custom_options("--dem-resolution 0.25 --orthophoto-resolution 0.25 --fast-orthophoto")
        names = {o["name"] for o in opts}
        assert "dem-resolution" in names
        assert "orthophoto-resolution" in names
        assert "fast-orthophoto" in names

        for o in opts:
            if o["name"] == "dem-resolution":
                assert o["value"] == 0.25
            if o["name"] == "fast-orthophoto":
                assert o["value"] is True

    def test_parse_custom_options_empty(self):
        from gemini.workers.odm.worker import _parse_custom_options, DEFAULT_OPTIONS

        opts = _parse_custom_options("")
        assert opts == DEFAULT_OPTIONS

    def test_parse_custom_options_list(self):
        from gemini.workers.odm.worker import _parse_custom_options

        input_opts = [{"name": "dsm", "value": True}]
        assert _parse_custom_options(input_opts) == input_opts


class TestOdmWorkerPipeline:
    """Test the full ODM worker pipeline with mock NodeODM and real MinIO."""

    def _make_worker(self, mock_nodeodm_url):
        """Create an OdmWorker configured for testing."""
        from gemini.workers.odm.worker import OdmWorker
        import gemini.workers.odm.worker as worker_module

        # Override MinIO connection to test instance
        worker_module.STORAGE_HOST = TEST_MINIO_HOST
        worker_module.STORAGE_PORT = TEST_MINIO_PORT
        worker_module.STORAGE_ACCESS_KEY = "gemini_test_user"
        worker_module.STORAGE_SECRET_KEY = "gemini_test_secret"
        worker_module.STORAGE_BUCKET = BUCKET
        worker_module.POLL_INTERVAL = 0.1  # fast polling for tests

        worker = OdmWorker(worker_id="test-odm-worker")
        worker._nodeodm = __import__(
            "gemini.workers.odm.nodeodm_client", fromlist=["NodeODMClient"]
        ).NodeODMClient(base_url=mock_nodeodm_url)

        return worker

    def test_successful_pipeline(self, mock_nodeodm, minio_client):
        """Full happy path: seed images → run worker → verify output in MinIO."""
        image_prefix = "test_odm/2024/exp/loc/pop/2024-06-15/DJI/RGB/Images/"
        output_prefix = "Processed/test_odm/2024/exp/loc/pop/2024-06-15/DJI/RGB/"

        try:
            _seed_test_images(minio_client, image_prefix, count=3)

            worker = self._make_worker(mock_nodeodm)
            result = worker.process(
                job_id=str(uuid4()),
                job_type="RUN_ODM",
                parameters={
                    "year": "test_odm/2024",
                    "experiment": "exp",
                    "location": "loc",
                    "population": "pop",
                    "date": "2024-06-15",
                    "platform": "DJI",
                    "sensor": "RGB",
                    "reconstruction_quality": "Default",
                },
            )

            assert result["image_count"] == 3
            assert "orthophoto_path" in result

            # Verify orthophoto was uploaded to MinIO
            ortho_path = result["orthophoto_path"]
            stat = minio_client.stat_object(BUCKET, ortho_path)
            assert stat.size > 0

            # Verify log was saved
            log_path = f"{output_prefix}odm_log.txt"
            log_stat = minio_client.stat_object(BUCKET, log_path)
            assert log_stat.size > 0

            # Read log content
            response = minio_client.get_object(BUCKET, log_path)
            log_content = response.read().decode()
            response.close()
            response.release_conn()
            assert "Starting OpenDroneMap" in log_content

        finally:
            _cleanup_prefix(minio_client, image_prefix)
            _cleanup_prefix(minio_client, output_prefix)

    def test_no_images_raises(self, mock_nodeodm, minio_client):
        """Worker should raise when no images found in MinIO."""
        worker = self._make_worker(mock_nodeodm)
        with pytest.raises(RuntimeError, match="No images found"):
            worker.process(
                job_id=str(uuid4()),
                job_type="RUN_ODM",
                parameters={
                    "year": "nonexistent",
                    "experiment": "exp",
                    "location": "loc",
                    "population": "pop",
                    "date": "2024-01-01",
                    "platform": "DJI",
                    "sensor": "RGB",
                },
            )

    def test_odm_failure_propagates(self, mock_nodeodm, minio_client):
        """Worker should raise RuntimeError when ODM reports failure."""
        image_prefix = "test_odm_fail/Images/"

        try:
            _seed_test_images(minio_client, image_prefix, count=2)
            MockNodeODMHandler.fail_next = True

            worker = self._make_worker(mock_nodeodm)
            with pytest.raises(RuntimeError, match="ODM processing failed"):
                worker.process(
                    job_id=str(uuid4()),
                    job_type="RUN_ODM",
                    parameters={
                        "year": "test_odm_fail",
                        "experiment": "",
                        "location": "",
                        "population": "",
                        "date": "",
                        "platform": "",
                        "sensor": "",
                    },
                )
        finally:
            _cleanup_prefix(minio_client, image_prefix)

    def test_custom_options_passed(self, mock_nodeodm, minio_client):
        """Verify custom CLI options are parsed and worker completes."""
        image_prefix = "test_odm_custom/2024/exp/loc/pop/2024-06-15/DJI/RGB/Images/"

        try:
            _seed_test_images(minio_client, image_prefix, count=2)

            worker = self._make_worker(mock_nodeodm)
            result = worker.process(
                job_id=str(uuid4()),
                job_type="RUN_ODM",
                parameters={
                    "year": "test_odm_custom/2024",
                    "experiment": "exp",
                    "location": "loc",
                    "population": "pop",
                    "date": "2024-06-15",
                    "platform": "DJI",
                    "sensor": "RGB",
                    "reconstruction_quality": "Custom",
                    "custom_options": "--dem-resolution 0.5 --orthophoto-resolution 0.5",
                },
            )

            assert result["image_count"] == 2
            assert "orthophoto_path" in result

        finally:
            _cleanup_prefix(minio_client, image_prefix)
            _cleanup_prefix(minio_client, "Processed/test_odm_custom/")
