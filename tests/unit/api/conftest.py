"""Fixtures for the API layer tests."""
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date, datetime


@pytest.fixture(autouse=True)
def mock_api_db_engine():
    """
    Auto-use fixture that replaces ``db_engine`` with a MagicMock
    everywhere it's been re-exported via ``from gemini.db.core.base import
    db_engine``. Most API classes delegate through their DB model
    (patched per-test), but some methods — notably ``Experiment.update``
    and ``Experiment.delete`` — hit ``db_engine`` directly, and some paths
    reach it transitively through the columnar record models
    (``trait_records.db_engine`` etc.). Without this fixture those calls
    reach a real Postgres and fail with the dummy credentials wired up by
    the root conftest.

    We patch every module that imports the name at load time (their
    binding is separate from the source attribute) plus the source module
    itself. Mirrors the equivalent mock in ``tests/unit/db/conftest.py``.
    """
    import sys

    mock_engine = MagicMock()
    mock_session = MagicMock()

    @contextmanager
    def get_session():
        yield mock_session

    mock_engine.get_session = get_session
    mock_engine.get_engine.return_value = MagicMock()

    # Find every already-loaded module that has a ``db_engine`` attribute
    # pointing at the real engine. ``from X import Y`` creates an
    # independent binding in the importing module, so patching only the
    # source module leaves those stale.
    from gemini.db.core import base as base_mod
    real_engine = base_mod.db_engine

    patchers = [patch.object(base_mod, "db_engine", mock_engine)]
    for name, module in list(sys.modules.items()):
        if module is base_mod or module is None:
            continue
        if not name.startswith("gemini"):
            continue
        if getattr(module, "db_engine", None) is real_engine:
            patchers.append(patch.object(module, "db_engine", mock_engine))

    for p in patchers:
        p.start()
    try:
        yield mock_engine, mock_session
    finally:
        for p in reversed(patchers):
            p.stop()


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
