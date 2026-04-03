"""Tests for storage configuration classes."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from gemini.storage.config.storage_config import (
    StorageConfig,
    LocalStorageConfig,
    MinioStorageConfig,
    S3StorageConfig,
)
from gemini.storage.exceptions import StorageConfigurationError


# ── StorageConfig (base) ──────────────────────────────────────────


class TestStorageConfig:
    def test_requires_provider(self):
        with pytest.raises(ValidationError):
            StorageConfig()

    def test_accepts_provider(self):
        cfg = StorageConfig(provider="test")
        assert cfg.provider == "test"
        assert cfg.base_path is None

    def test_base_path_optional(self):
        cfg = StorageConfig(provider="test", base_path="/data")
        assert cfg.base_path == "/data"

    def test_forbids_extra_fields(self):
        with pytest.raises(ValidationError):
            StorageConfig(provider="test", unknown_field="bad")


# ── LocalStorageConfig ────────────────────────────────────────────


class TestLocalStorageConfig:
    def test_defaults(self, tmp_path):
        cfg = LocalStorageConfig(root_directory=tmp_path)
        assert cfg.provider == "local"
        assert cfg.create_directory is True
        assert cfg.root_directory == tmp_path.resolve()

    def test_provider_is_frozen_after_creation(self, tmp_path):
        cfg = LocalStorageConfig(root_directory=tmp_path)
        with pytest.raises(ValidationError):
            cfg.provider = "other"

    def test_requires_root_directory(self):
        with pytest.raises(ValidationError):
            LocalStorageConfig()

    def test_resolves_root_directory(self, tmp_path):
        cfg = LocalStorageConfig(root_directory=tmp_path / "sub" / ".." / "actual")
        assert ".." not in str(cfg.root_directory)


# ── MinioStorageConfig ────────────────────────────────────────────


class TestMinioStorageConfig:
    def test_valid_config(self):
        cfg = MinioStorageConfig(
            endpoint="localhost:9000",
            access_key="key",
            secret_key="secret",
            bucket_name="bucket",
        )
        assert cfg.provider == "minio"
        assert cfg.secure is True
        assert cfg.region is None

    def test_requires_endpoint(self):
        with pytest.raises(ValidationError):
            MinioStorageConfig(
                access_key="key", secret_key="secret", bucket_name="bucket"
            )

    def test_endpoint_rejects_protocol(self):
        with pytest.raises((ValidationError, StorageConfigurationError)):
            MinioStorageConfig(
                endpoint="http://localhost:9000",
                access_key="key",
                secret_key="secret",
                bucket_name="bucket",
            )

    def test_requires_both_credentials(self):
        with pytest.raises((ValidationError, StorageConfigurationError)):
            MinioStorageConfig(
                endpoint="localhost:9000",
                access_key="",
                secret_key="secret",
                bucket_name="bucket",
            )

    def test_custom_fields(self):
        cfg = MinioStorageConfig(
            endpoint="host:9000",
            access_key="key",
            secret_key="secret",
            bucket_name="b",
            secure=False,
            region="us-west-1",
        )
        assert cfg.secure is False
        assert cfg.region == "us-west-1"


# ── S3StorageConfig ───────────────────────────────────────────────


class TestS3StorageConfig:
    def test_valid_config(self):
        cfg = S3StorageConfig(
            region="us-east-1",
            access_key="AKID",
            secret_key="SECRET",
            bucket_name="my-bucket",
        )
        assert cfg.provider == "s3"
        assert cfg.endpoint_url is None

    def test_requires_region(self):
        with pytest.raises(ValidationError):
            S3StorageConfig(
                access_key="AKID", secret_key="SECRET", bucket_name="b"
            )

    def test_requires_both_credentials(self):
        with pytest.raises((ValidationError, StorageConfigurationError)):
            S3StorageConfig(
                region="us-east-1",
                access_key="",
                secret_key="SECRET",
                bucket_name="b",
            )

    def test_optional_endpoint_url(self):
        cfg = S3StorageConfig(
            region="us-east-1",
            access_key="AKID",
            secret_key="SECRET",
            bucket_name="b",
            endpoint_url="http://localhost:4566",
        )
        assert cfg.endpoint_url == "http://localhost:4566"
