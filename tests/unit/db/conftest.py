"""
Fixtures for the DB layer tests.

Provides a mock database engine that patches `gemini.db.core.base.db_engine`
so that no real database connection is needed during unit tests.
"""
import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager


@pytest.fixture(autouse=True)
def mock_db_engine():
    """
    Auto-use fixture that replaces the global db_engine in gemini.db.core.base
    with a MagicMock. The mock provides a working get_session() context manager
    that yields a mock session, and a get_engine() that returns a mock engine.
    """
    mock_engine = MagicMock()
    mock_session = MagicMock()

    @contextmanager
    def get_session():
        yield mock_session

    mock_engine.get_session = get_session
    mock_engine.get_engine.return_value = MagicMock()

    with patch("gemini.db.core.base.db_engine", mock_engine):
        yield mock_engine, mock_session
