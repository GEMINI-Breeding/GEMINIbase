"""Smoke tests to verify import guards work correctly."""
import pytest


class TestImportGuards:
    """Verify that gemini modules can be imported without infrastructure."""

    def test_import_settings(self):
        from gemini.config.settings import GEMINISettings
        settings = GEMINISettings()
        assert settings.GEMINI_DB_USER is not None

    def test_import_manager(self):
        from gemini.manager import GEMINIManager, GEMINIComponentType
        manager = GEMINIManager()
        assert manager is not None

    def test_import_db_base(self):
        from gemini.db.core.base import BaseModel
        assert BaseModel is not None

    def test_import_db_engine(self):
        from gemini.db.core.engine import DatabaseEngine
        assert DatabaseEngine is not None

    def test_import_api_base(self):
        from gemini.api.base import APIBase
        assert APIBase is not None

    def test_import_storage_providers(self):
        from gemini.storage.providers.minio_storage import MinioStorageProvider
        from gemini.storage.providers.local_storage import LocalStorageProvider
        assert MinioStorageProvider is not None
        assert LocalStorageProvider is not None

    def test_import_enums(self):
        from gemini.api.enums import (
            GEMINIDataFormat,
            GEMINISensorType,
            GEMINIDatasetType,
            GEMINIDataType,
            GEMINITraitLevel,
        )
        assert len(GEMINIDataFormat) > 0
