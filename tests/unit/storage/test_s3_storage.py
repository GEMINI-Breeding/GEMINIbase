"""Tests for S3StorageProvider."""

import io
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

from gemini.storage.config.storage_config import S3StorageConfig
from gemini.storage.exceptions import (
    StorageAuthError,
    StorageConnectionError,
    StorageDeleteError,
    StorageDownloadError,
    StorageError,
    StorageFileNotFoundError,
    StorageInitializationError,
    StorageUploadError,
)


# Import the provider (exception classes already set up in root conftest.py)
from gemini.storage.providers.s3_storage import S3StorageProvider

# Use the same ClientError class that s3_storage.py imported
from botocore.exceptions import ClientError as _ClientError


def _make_config(**overrides):
    defaults = dict(
        region="us-east-1",
        access_key="AKID",
        secret_key="SECRET",
        bucket_name="test-bucket",
    )
    defaults.update(overrides)
    return S3StorageConfig(**defaults)


def _make_client_error(code="404", message="Not Found"):
    """Create a ClientError whose ``response['Error']['Code']`` returns *code*."""
    return _ClientError(code, message)


@pytest.fixture
def s3_provider():
    """Return an S3StorageProvider with mocked boto3 client."""
    config = _make_config()
    provider = S3StorageProvider(config)
    # Replace the client created via the mocked boto3 with a fresh MagicMock
    provider.client = MagicMock()
    return provider


# ── __init__ ──────────────────────────────────────────────────────


class TestInit:
    def test_creates_client_with_correct_bucket(self):
        config = _make_config()
        provider = S3StorageProvider(config)
        assert provider.bucket_name == "test-bucket"
        assert provider.config is config


# ── initialize ────────────────────────────────────────────────────


class TestInitialize:
    def test_returns_true_when_bucket_exists(self, s3_provider):
        s3_provider.client.head_bucket.return_value = {}
        assert s3_provider.initialize() is True

    def test_raises_when_bucket_not_found(self, s3_provider):
        s3_provider.client.head_bucket.side_effect = _make_client_error("404")
        with pytest.raises(StorageInitializationError, match="not found"):
            s3_provider.initialize()

    def test_raises_auth_error_on_403(self, s3_provider):
        s3_provider.client.head_bucket.side_effect = _make_client_error("403")
        with pytest.raises(StorageAuthError, match="Access denied"):
            s3_provider.initialize()


# ── upload_file ───────────────────────────────────────────────────


class TestUploadFile:
    def test_with_data_stream_calls_upload_fileobj(self, s3_provider):
        # file_exists for get_download_url
        s3_provider.client.head_object.return_value = {}
        s3_provider.client.generate_presigned_url.return_value = "https://url"
        stream = io.BytesIO(b"hello")
        url = s3_provider.upload_file("key.txt", data_stream=stream)
        s3_provider.client.upload_fileobj.assert_called_once()
        assert url == "https://url"

    def test_with_input_file_path_calls_upload_file(self, s3_provider, tmp_path):
        f = tmp_path / "local.txt"
        f.write_bytes(b"data")
        s3_provider.client.head_object.return_value = {}
        s3_provider.client.generate_presigned_url.return_value = "https://url"
        url = s3_provider.upload_file("key.txt", input_file_path=f)
        s3_provider.client.upload_file.assert_called_once()

    def test_raises_upload_error_without_stream_or_path(self, s3_provider):
        with pytest.raises(StorageUploadError, match="Either data_stream or input_file_path"):
            s3_provider.upload_file("key.txt")

    def test_passes_content_type_and_metadata(self, s3_provider):
        s3_provider.client.head_object.return_value = {}
        s3_provider.client.generate_presigned_url.return_value = "https://url"
        stream = io.BytesIO(b"x")
        s3_provider.upload_file(
            "key.txt",
            data_stream=stream,
            content_type="text/plain",
            metadata={"author": "test"},
        )
        call_kwargs = s3_provider.client.upload_fileobj.call_args
        extra = call_kwargs.kwargs.get("ExtraArgs") or call_kwargs[1].get("ExtraArgs")
        assert extra["ContentType"] == "text/plain"
        assert extra["Metadata"]["author"] == "test"

    def test_raises_upload_error_on_client_error(self, s3_provider):
        s3_provider.client.upload_fileobj.side_effect = _make_client_error("500", "Internal")
        stream = io.BytesIO(b"data")
        with pytest.raises(StorageUploadError):
            s3_provider.upload_file("key.txt", data_stream=stream)

    def test_raises_auth_error_on_access_denied(self, s3_provider):
        s3_provider.client.upload_fileobj.side_effect = _make_client_error("AccessDenied")
        stream = io.BytesIO(b"data")
        with pytest.raises(StorageAuthError):
            s3_provider.upload_file("key.txt", data_stream=stream)


# ── download_file ─────────────────────────────────────────────────


class TestDownloadFile:
    def test_downloads_file(self, s3_provider, tmp_path):
        dest = tmp_path / "out.txt"
        result = s3_provider.download_file("key.txt", str(dest))
        s3_provider.client.download_file.assert_called_once()
        assert result == dest

    def test_raises_not_found_on_404(self, s3_provider, tmp_path):
        s3_provider.client.download_file.side_effect = _make_client_error("404")
        with pytest.raises(StorageFileNotFoundError):
            s3_provider.download_file("missing.txt", str(tmp_path / "x.txt"))

    def test_raises_auth_error_on_403(self, s3_provider, tmp_path):
        s3_provider.client.download_file.side_effect = _make_client_error("403", "AccessDenied")
        with pytest.raises(StorageAuthError):
            s3_provider.download_file("key.txt", str(tmp_path / "x.txt"))


# ── delete_file ───────────────────────────────────────────────────


class TestDeleteFile:
    def test_calls_delete_object(self, s3_provider):
        assert s3_provider.delete_file("key.txt") is True
        s3_provider.client.delete_object.assert_called_once()

    def test_raises_delete_error_on_client_error(self, s3_provider):
        s3_provider.client.delete_object.side_effect = _make_client_error("500", "Err")
        with pytest.raises(StorageDeleteError):
            s3_provider.delete_file("key.txt")

    def test_raises_auth_error_on_access_denied(self, s3_provider):
        s3_provider.client.delete_object.side_effect = _make_client_error("AccessDenied")
        with pytest.raises(StorageAuthError):
            s3_provider.delete_file("key.txt")


# ── get_download_url ──────────────────────────────────────────────


class TestGetDownloadUrl:
    def test_returns_presigned_url(self, s3_provider):
        s3_provider.client.head_object.return_value = {}
        s3_provider.client.generate_presigned_url.return_value = "https://signed"
        url = s3_provider.get_download_url("key.txt")
        assert url == "https://signed"

    def test_accepts_timedelta_expires(self, s3_provider):
        s3_provider.client.head_object.return_value = {}
        s3_provider.client.generate_presigned_url.return_value = "https://url"
        s3_provider.get_download_url("key.txt", expires=timedelta(hours=2))
        call_kwargs = s3_provider.client.generate_presigned_url.call_args
        assert call_kwargs.kwargs.get("ExpiresIn") == 7200 or call_kwargs[1].get("ExpiresIn") == 7200


# ── list_files ────────────────────────────────────────────────────


class TestListFiles:
    def test_returns_keys(self, s3_provider):
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "a.txt"}, {"Key": "b.txt"}]}
        ]
        s3_provider.client.get_paginator.return_value = paginator
        result = s3_provider.list_files()
        assert result == ["a.txt", "b.txt"]

    def test_handles_empty_pages(self, s3_provider):
        paginator = MagicMock()
        paginator.paginate.return_value = [{}]
        s3_provider.client.get_paginator.return_value = paginator
        result = s3_provider.list_files()
        assert result == []

    def test_passes_prefix(self, s3_provider):
        paginator = MagicMock()
        paginator.paginate.return_value = []
        s3_provider.client.get_paginator.return_value = paginator
        s3_provider.list_files(prefix="data/")
        call_kwargs = paginator.paginate.call_args
        assert call_kwargs.kwargs.get("Prefix") == "data/" or call_kwargs[1].get("Prefix") == "data/"


# ── file_exists ───────────────────────────────────────────────────


class TestFileExists:
    def test_true_when_head_object_succeeds(self, s3_provider):
        s3_provider.client.head_object.return_value = {}
        assert s3_provider.file_exists("key.txt") is True

    def test_false_on_404(self, s3_provider):
        s3_provider.client.head_object.side_effect = _make_client_error("404")
        assert s3_provider.file_exists("missing.txt") is False

    def test_raises_auth_error_on_403(self, s3_provider):
        s3_provider.client.head_object.side_effect = _make_client_error("403", "AccessDenied")
        with pytest.raises(StorageAuthError):
            s3_provider.file_exists("key.txt")


# ── get_file_metadata ─────────────────────────────────────────────


class TestGetFileMetadata:
    def test_returns_expected_keys(self, s3_provider):
        s3_provider.client.head_object.return_value = {
            "ContentLength": 2048,
            "ETag": '"etag123"',
            "LastModified": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "ContentType": "application/json",
            "Metadata": {"custom": "val"},
        }
        meta = s3_provider.get_file_metadata("key.txt")
        assert meta["size"] == 2048
        assert meta["etag"] == "etag123"
        assert meta["content_type"] == "application/json"
        assert meta["metadata"] == {"custom": "val"}
        assert meta["object_name"] == "key.txt"

    def test_raises_not_found_on_404(self, s3_provider):
        s3_provider.client.head_object.side_effect = _make_client_error("404")
        with pytest.raises(StorageFileNotFoundError):
            s3_provider.get_file_metadata("nope.txt")


# ── healthcheck ───────────────────────────────────────────────────


class TestHealthcheck:
    def test_returns_true_on_success(self, s3_provider):
        s3_provider.client.head_bucket.return_value = {}
        assert s3_provider.healthcheck() is True

    def test_raises_connection_error_on_failure(self, s3_provider):
        s3_provider.client.head_bucket.side_effect = _make_client_error("500", "err")
        with pytest.raises(StorageConnectionError):
            s3_provider.healthcheck()

    def test_raises_auth_error_on_403(self, s3_provider):
        s3_provider.client.head_bucket.side_effect = _make_client_error("403")
        with pytest.raises(StorageAuthError):
            s3_provider.healthcheck()
