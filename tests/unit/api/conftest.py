"""Fixtures for the API layer tests."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date, datetime


@pytest.fixture
def mock_minio_storage_provider():
    """Patches gemini.api.base.minio_storage_provider with a MagicMock."""
    provider = MagicMock()
    provider.upload_file.return_value = "minio://test-bucket/test-file.txt"
    provider.download_file.return_value = "/tmp/downloaded_file.txt"
    provider.file_exists.return_value = True
    provider.get_download_url.return_value = "http://presigned-url/test-file.txt"
    provider.delete_file.return_value = True
    with patch("gemini.api.base.minio_storage_provider", provider):
        yield provider


@pytest.fixture
def sample_uuid():
    """Provides a consistent test UUID."""
    return uuid4()


@pytest.fixture
def sample_date():
    """Provides a consistent test date."""
    return date(2024, 6, 15)


@pytest.fixture
def sample_datetime():
    """Provides a consistent test datetime."""
    return datetime(2024, 6, 15, 10, 30, 0)


def make_mock_db_instance(**kwargs):
    """Helper to create a mock DB instance with attribute access."""
    mock = MagicMock()
    for key, value in kwargs.items():
        setattr(mock, key, value)
    return mock
