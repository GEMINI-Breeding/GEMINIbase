"""Tests for storage exception hierarchy."""

import pytest
from gemini.storage.exceptions import (
    StorageError,
    StorageConnectionError,
    StorageAuthError,
    StorageFileNotFoundError,
    StorageUploadError,
    StorageDownloadError,
    StorageDeleteError,
    StorageInitializationError,
    StorageConfigurationError,
)


class TestExceptionHierarchy:
    """Verify every custom exception exists and inherits from StorageError."""

    @pytest.mark.parametrize(
        "exc_class",
        [
            StorageConnectionError,
            StorageAuthError,
            StorageFileNotFoundError,
            StorageUploadError,
            StorageDownloadError,
            StorageDeleteError,
            StorageInitializationError,
            StorageConfigurationError,
        ],
    )
    def test_inherits_from_storage_error(self, exc_class):
        assert issubclass(exc_class, StorageError)

    def test_storage_error_inherits_from_exception(self):
        assert issubclass(StorageError, Exception)

    @pytest.mark.parametrize(
        "exc_class",
        [
            StorageError,
            StorageConnectionError,
            StorageAuthError,
            StorageFileNotFoundError,
            StorageUploadError,
            StorageDownloadError,
            StorageDeleteError,
            StorageInitializationError,
            StorageConfigurationError,
        ],
    )
    def test_can_be_raised_and_caught(self, exc_class):
        with pytest.raises(exc_class):
            raise exc_class("test message")

    @pytest.mark.parametrize(
        "exc_class",
        [
            StorageError,
            StorageConnectionError,
            StorageAuthError,
            StorageFileNotFoundError,
            StorageUploadError,
            StorageDownloadError,
            StorageDeleteError,
            StorageInitializationError,
            StorageConfigurationError,
        ],
    )
    def test_message_preserved(self, exc_class):
        err = exc_class("specific message")
        assert str(err) == "specific message"

    def test_all_subclasses_caught_by_storage_error(self):
        for cls in [
            StorageConnectionError,
            StorageAuthError,
            StorageFileNotFoundError,
            StorageUploadError,
            StorageDownloadError,
            StorageDeleteError,
            StorageInitializationError,
            StorageConfigurationError,
        ]:
            with pytest.raises(StorageError):
                raise cls("caught by base")
