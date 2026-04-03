"""Tests for StorageFactory."""

import pytest
from unittest.mock import MagicMock, patch

from gemini.storage.factory.storage_factory import StorageFactory
from gemini.storage.config.storage_config import (
    LocalStorageConfig,
    MinioStorageConfig,
    S3StorageConfig,
)
from gemini.storage.providers.local_storage import LocalStorageProvider
from gemini.storage.providers.minio_storage import MinioStorageProvider
from gemini.storage.providers.s3_storage import S3StorageProvider
from gemini.storage.exceptions import StorageInitializationError


@pytest.fixture(autouse=True)
def reset_factory():
    """Reset the singleton and restore the default registry after each test."""
    original_providers = StorageFactory._providers.copy()
    StorageFactory.reset_provider()
    yield
    StorageFactory._providers = original_providers
    StorageFactory.reset_provider()


# ── Registry ──────────────────────────────────────────────────────


class TestRegistry:
    def test_default_providers_registered(self):
        assert "local" in StorageFactory._providers
        assert "minio" in StorageFactory._providers
        assert "s3" in StorageFactory._providers

    def test_register_new_provider(self):
        mock_class = MagicMock()
        StorageFactory.register_provider("custom", mock_class)
        assert StorageFactory._providers["custom"] is mock_class

    def test_register_duplicate_raises(self):
        with pytest.raises(ValueError, match="already registered"):
            StorageFactory.register_provider("local", LocalStorageProvider)


# ── create_provider ───────────────────────────────────────────────


class TestCreateProvider:
    def test_creates_local_provider(self, tmp_path):
        config = LocalStorageConfig(root_directory=tmp_path, create_directory=True)
        provider = StorageFactory.create_provider(config)
        assert isinstance(provider, LocalStorageProvider)

    def test_raises_for_unknown_provider(self):
        config = MagicMock()
        config.provider = "unknown"
        with pytest.raises(ValueError, match="Unsupported"):
            StorageFactory.create_provider(config)

    def test_raises_initialization_error_on_failure(self):
        config = MagicMock()
        config.provider = "local"
        config.root_directory = "/nonexistent/path/that/should/not/exist"
        config.create_directory = False
        with pytest.raises(StorageInitializationError):
            StorageFactory.create_provider(config)


# ── get_provider (singleton) ──────────────────────────────────────


class TestGetProvider:
    def test_returns_same_instance(self, tmp_path):
        config = LocalStorageConfig(root_directory=tmp_path, create_directory=True)
        p1 = StorageFactory.get_provider(config)
        p2 = StorageFactory.get_provider(config)
        assert p1 is p2

    def test_raises_without_config(self):
        with pytest.raises(NotImplementedError):
            StorageFactory.get_provider()

    def test_reset_clears_singleton(self, tmp_path):
        config = LocalStorageConfig(root_directory=tmp_path, create_directory=True)
        p1 = StorageFactory.get_provider(config)
        StorageFactory.reset_provider()
        assert StorageFactory._instance is None
