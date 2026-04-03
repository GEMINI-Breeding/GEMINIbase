"""Unit test fixtures - shared across all unit tests."""
import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, date


@pytest.fixture
def mock_storage_provider():
    """Mock MinioStorageProvider for API tests."""
    provider = MagicMock()
    provider.upload_file.return_value = "http://test/file.txt"
    provider.download_file.return_value = "/tmp/file.txt"
    provider.file_exists.return_value = True
    provider.get_download_url.return_value = "http://presigned-url"
    provider.list_files.return_value = ["file1.txt", "file2.txt"]
    provider.get_file_metadata.return_value = {
        "bucket_name": "test",
        "object_name": "file.txt",
        "size": 1024,
        "etag": "abc",
        "last_modified": "2024-01-01",
        "content_type": "text/plain",
        "metadata": {},
    }
    provider.healthcheck.return_value = True
    provider.initialize.return_value = True
    return provider


@pytest.fixture
def sample_uuid():
    """Provides a consistent test UUID."""
    return uuid4()


@pytest.fixture
def sample_datetime():
    """Provides a consistent test datetime."""
    return datetime(2024, 1, 15, 12, 0, 0)


@pytest.fixture
def sample_date():
    """Provides a consistent test date."""
    return date(2024, 1, 15)
