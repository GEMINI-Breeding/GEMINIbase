"""Tests for MinioStorageProvider."""

import io
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from gemini.storage.config.storage_config import MinioStorageConfig
from gemini.storage.exceptions import (
    StorageConnectionError,
    StorageFileNotFoundError,
    StorageUploadError,
    StorageInitializationError,
)


# Import the provider (S3Error already set up in root conftest.py)
from gemini.storage.providers.minio_storage import MinioStorageProvider

# Use the same S3Error class that minio_storage.py imported
from minio.error import S3Error as _S3Error


def _make_config(**overrides):
    defaults = dict(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket_name="test-bucket",
        secure=False,
    )
    defaults.update(overrides)
    return MinioStorageConfig(**defaults)


def _make_s3_error(code="NoSuchKey", message="not found"):
    """Create an S3Error whose str() contains the given *code*."""
    return _S3Error(code, message)


@pytest.fixture
def minio_provider():
    """Return a MinioStorageProvider with a mocked Minio client."""
    config = _make_config()
    provider = MinioStorageProvider(config)
    # Replace the auto-generated mock client with a fresh one.
    provider.client = MagicMock()
    return provider


# ── __init__ ──────────────────────────────────────────────────────


class TestInit:
    def test_creates_client_with_correct_params(self):
        config = _make_config()
        provider = MinioStorageProvider(config)
        assert provider.bucket_name == "test-bucket"
        assert provider.config is config


# ── initialize ────────────────────────────────────────────────────


class TestInitialize:
    def test_creates_bucket_if_not_exists(self, minio_provider):
        minio_provider.client.bucket_exists.return_value = False
        result = minio_provider.initialize()
        assert result is True
        minio_provider.client.make_bucket.assert_called_once()

    def test_skips_bucket_creation_if_exists(self, minio_provider):
        minio_provider.client.bucket_exists.return_value = True
        minio_provider.initialize()
        minio_provider.client.make_bucket.assert_not_called()


# ── upload_file ───────────────────────────────────────────────────


class TestUploadFile:
    def test_with_data_stream_calls_put_object(self, minio_provider):
        minio_provider.client.stat_object.return_value = MagicMock()  # file_exists
        minio_provider.client.presigned_get_object.return_value = "http://url"
        stream = io.BytesIO(b"hello")
        url = minio_provider.upload_file("obj.txt", data_stream=stream)
        minio_provider.client.put_object.assert_called_once()
        assert url == "http://url"

    def test_with_input_file_path_calls_fput_object(self, minio_provider, tmp_path):
        f = tmp_path / "local.txt"
        f.write_bytes(b"data")
        minio_provider.client.stat_object.return_value = MagicMock()
        minio_provider.client.presigned_get_object.return_value = "http://url"
        url = minio_provider.upload_file("obj.txt", input_file_path=f)
        minio_provider.client.fput_object.assert_called_once()

    @patch("gemini.storage.providers.minio_storage.time.sleep")
    def test_retry_with_exponential_backoff(self, mock_sleep, minio_provider):
        err = _make_s3_error("InternalError", "temporary")
        # Fail twice, succeed on third
        minio_provider.client.put_object.side_effect = [err, err, None]
        minio_provider.client.stat_object.return_value = MagicMock()
        minio_provider.client.presigned_get_object.return_value = "http://ok"
        stream = io.BytesIO(b"data")
        url = minio_provider.upload_file("obj.txt", data_stream=stream)
        assert url == "http://ok"
        assert mock_sleep.call_count == 2
        # Check exponential backoff: 1*2^0=1, 1*2^1=2
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)

    @patch("gemini.storage.providers.minio_storage.time.sleep")
    def test_raises_after_max_retries(self, mock_sleep, minio_provider):
        err = _make_s3_error("InternalError", "fail")
        minio_provider.client.put_object.side_effect = err
        stream = io.BytesIO(b"data")
        with pytest.raises(StorageUploadError, match="after 5 attempts"):
            minio_provider.upload_file("obj.txt", data_stream=stream)

    def test_raises_value_error_without_stream_or_path(self, minio_provider):
        with pytest.raises(ValueError, match="Either data_stream or input_file_path"):
            minio_provider.upload_file("obj.txt")


# ── download_file ─────────────────────────────────────────────────


class TestDownloadFile:
    def test_calls_fget_object(self, minio_provider, tmp_path):
        dest = tmp_path / "out.txt"
        result = minio_provider.download_file("obj.txt", str(dest))
        minio_provider.client.fget_object.assert_called_once()
        assert result == dest

    def test_raises_file_not_found_for_nosuchkey(self, minio_provider, tmp_path):
        err = _make_s3_error("NoSuchKey")
        minio_provider.client.fget_object.side_effect = err
        with pytest.raises(StorageFileNotFoundError):
            minio_provider.download_file("missing.txt", str(tmp_path / "x.txt"))


# ── download_file_stream ──────────────────────────────────────────


class TestDownloadFileStream:
    def test_returns_response(self, minio_provider):
        mock_response = MagicMock()
        minio_provider.client.get_object.return_value = mock_response
        result = minio_provider.download_file_stream("obj.txt")
        assert result is mock_response


# ── delete_file ───────────────────────────────────────────────────


class TestDeleteFile:
    def test_calls_remove_object(self, minio_provider):
        assert minio_provider.delete_file("obj.txt") is True
        minio_provider.client.remove_object.assert_called_once()


# ── get_download_url ──────────────────────────────────────────────


class TestGetDownloadUrl:
    def test_calls_presigned_get_object(self, minio_provider):
        minio_provider.client.stat_object.return_value = MagicMock()
        minio_provider.client.presigned_get_object.return_value = "http://signed"
        url = minio_provider.get_download_url("obj.txt")
        assert url == "http://signed"
        minio_provider.client.presigned_get_object.assert_called_once()

    def test_raises_for_missing_file(self, minio_provider):
        minio_provider.client.stat_object.side_effect = _make_s3_error("NoSuchKey")
        from gemini.storage.exceptions import StorageError
        with pytest.raises(StorageError):
            minio_provider.get_download_url("nope.txt")


# ── list_files ────────────────────────────────────────────────────


class TestListFiles:
    def test_returns_object_names(self, minio_provider):
        obj1 = MagicMock()
        obj1.object_name = "a.txt"
        obj2 = MagicMock()
        obj2.object_name = "b.txt"
        minio_provider.client.list_objects.return_value = [obj1, obj2]
        result = minio_provider.list_files()
        assert result == ["a.txt", "b.txt"]


# ── file_exists ───────────────────────────────────────────────────


class TestFileExists:
    def test_true_when_stat_succeeds(self, minio_provider):
        minio_provider.client.stat_object.return_value = MagicMock()
        assert minio_provider.file_exists("obj.txt") is True

    def test_false_on_s3_error(self, minio_provider):
        minio_provider.client.stat_object.side_effect = _make_s3_error("NoSuchKey")
        assert minio_provider.file_exists("nope.txt") is False


# ── get_file_metadata ─────────────────────────────────────────────


class TestGetFileMetadata:
    def test_returns_expected_keys(self, minio_provider):
        stat = MagicMock()
        stat.bucket_name = "test-bucket"
        stat.object_name = "obj.txt"
        stat.size = 1024
        stat.etag = "abc123"
        stat.last_modified = datetime(2025, 1, 1)
        stat.content_type = "text/plain"
        stat.metadata = {"custom": "value"}
        minio_provider.client.stat_object.return_value = stat
        meta = minio_provider.get_file_metadata("obj.txt")
        assert meta["size"] == 1024
        assert meta["content_type"] == "text/plain"
        assert meta["metadata"] == {"custom": "value"}
        assert meta["object_name"] == "obj.txt"

    def test_raises_for_nosuchkey(self, minio_provider):
        minio_provider.client.stat_object.side_effect = _make_s3_error("NoSuchKey")
        with pytest.raises(StorageFileNotFoundError):
            minio_provider.get_file_metadata("nope.txt")


# ── bucket_exists ─────────────────────────────────────────────────


class TestBucketExists:
    def test_delegates_to_client(self, minio_provider):
        minio_provider.client.bucket_exists.return_value = True
        assert minio_provider.bucket_exists("my-bucket") is True
        minio_provider.client.bucket_exists.assert_called_once_with("my-bucket")


# ── healthcheck ───────────────────────────────────────────────────


class TestHealthcheck:
    def test_returns_true_on_success(self, minio_provider):
        minio_provider.client.bucket_exists.return_value = True
        assert minio_provider.healthcheck() is True

    def test_raises_on_s3_error(self, minio_provider):
        minio_provider.client.bucket_exists.side_effect = _make_s3_error("AccessDenied")
        with pytest.raises(StorageConnectionError):
            minio_provider.healthcheck()

    def test_raises_on_generic_exception(self, minio_provider):
        minio_provider.client.bucket_exists.side_effect = Exception("down")
        with pytest.raises(StorageConnectionError):
            minio_provider.healthcheck()
