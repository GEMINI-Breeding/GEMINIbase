"""
Tests for gemini.db.core.engine.DatabaseEngine.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from sqlalchemy import exc

from gemini.db.config import DatabaseConfig
from gemini.db.core.engine import DatabaseEngine


@pytest.fixture
def db_config():
    return DatabaseConfig(database_url="postgresql://user:pass@localhost:5432/testdb")


class TestDatabaseEngineInit:
    """Tests for DatabaseEngine initialization."""

    def test_init_raises_without_config(self):
        with pytest.raises(ValueError, match="Database configuration is required"):
            DatabaseEngine(config=None)

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_init_calls_setup_engine(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_create_async.return_value = MagicMock()

        db = DatabaseEngine(config=db_config)

        mock_create_engine.assert_called_once()
        assert db._engine is mock_engine

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_init_with_pre_existing_engine(self, mock_event, mock_create_engine, mock_create_async, db_config):
        existing_engine = MagicMock()
        existing_engine.pool = MagicMock()
        mock_create_async.return_value = MagicMock()

        db = DatabaseEngine(config=db_config, engine=existing_engine)

        mock_create_engine.assert_not_called()
        assert db._engine is existing_engine

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_init_with_pre_existing_async_engine(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        existing_async = MagicMock()

        db = DatabaseEngine(config=db_config, async_engine=existing_async)

        mock_create_async.assert_not_called()
        assert db._async_engine is existing_async


class TestSetupEngine:
    """Tests for setup_engine method."""

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_setup_engine_creates_with_correct_params(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_create_async.return_value = MagicMock()

        db = DatabaseEngine(config=db_config)

        call_kwargs = mock_create_engine.call_args
        # Note: setup_async_engine mutates config.database_url in-place,
        # so compare against the original URL pattern
        assert "postgresql" in call_kwargs[0][0]
        assert "user:pass@localhost:5432/testdb" in call_kwargs[0][0]
        assert call_kwargs[1]["pool_size"] == db_config.pool_size
        assert call_kwargs[1]["max_overflow"] == db_config.max_overflow
        assert call_kwargs[1]["pool_timeout"] == db_config.pool_timeout
        assert call_kwargs[1]["pool_recycle"] == db_config.pool_recycle
        assert call_kwargs[1]["pool_pre_ping"] is True
        assert call_kwargs[1]["echo"] == db_config.echo_sql

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_setup_engine_skips_if_already_set(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_create_async.return_value = MagicMock()

        db = DatabaseEngine(config=db_config)
        assert mock_create_engine.call_count == 1

        # Calling again should not create a new engine
        db.setup_engine()
        assert mock_create_engine.call_count == 1


class TestSetupAsyncEngine:
    """Tests for setup_async_engine method."""

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_setup_async_engine_creates_engine(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_async_engine = MagicMock()
        mock_create_async.return_value = mock_async_engine

        db = DatabaseEngine(config=db_config)

        mock_create_async.assert_called_once()
        assert db._async_engine is mock_async_engine

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_setup_async_engine_uses_asyncpg_dialect(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_create_async.return_value = MagicMock()

        db = DatabaseEngine(config=db_config)

        async_call_args = mock_create_async.call_args
        url = async_call_args[0][0]
        assert "postgresql+asyncpg" in url


class TestGetSession:
    """Tests for get_session context manager."""

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_get_session_yields_session(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_create_async.return_value = MagicMock()

        mock_session = MagicMock()
        db = DatabaseEngine(config=db_config)
        db._session_factory = MagicMock(return_value=mock_session)

        with db.get_session() as session:
            assert session is mock_session

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_get_session_commits_on_success(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_create_async.return_value = MagicMock()

        mock_session = MagicMock()
        db = DatabaseEngine(config=db_config)
        db._session_factory = MagicMock(return_value=mock_session)

        with db.get_session() as session:
            pass

        mock_session.flush.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_get_session_rolls_back_on_error(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_create_async.return_value = MagicMock()

        mock_session = MagicMock()
        db = DatabaseEngine(config=db_config)
        db._session_factory = MagicMock(return_value=mock_session)

        with pytest.raises(RuntimeError):
            with db.get_session() as session:
                raise RuntimeError("test error")

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()


class TestCheckHealth:
    """Tests for check_health method."""

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_check_health_returns_true(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_create_async.return_value = MagicMock()

        db = DatabaseEngine(config=db_config)
        assert db.check_health() is True

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_check_health_returns_false_on_failure(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_engine.connect.side_effect = exc.DBAPIError(
            statement="SELECT 1", params={}, orig=Exception("connection failed")
        )
        mock_create_engine.return_value = mock_engine
        mock_create_async.return_value = MagicMock()

        db = DatabaseEngine(config=db_config)
        assert db.check_health() is False


class TestGetPoolStatus:
    """Tests for get_pool_status method."""

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_get_pool_status_returns_dict(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0

        mock_engine = MagicMock()
        mock_engine.pool = mock_pool
        mock_create_engine.return_value = mock_engine
        mock_create_async.return_value = MagicMock()

        db = DatabaseEngine(config=db_config)
        status = db.get_pool_status()

        assert status == {
            "size": 10,
            "checkedin": 8,
            "checkedout": 2,
            "overflow": 0,
            "checkedout_overflow": 0,
        }


class TestDispose:
    """Tests for dispose method."""

    @patch("gemini.db.core.engine.asyncio")
    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_dispose_disposes_both_engines(self, mock_event, mock_create_engine, mock_create_async, mock_asyncio, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_async_engine = MagicMock()
        mock_create_async.return_value = mock_async_engine

        db = DatabaseEngine(config=db_config)
        db.dispose()

        mock_engine.dispose.assert_called_once()
        mock_asyncio.run.assert_called_once()

    @patch("gemini.db.core.engine.asyncio")
    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_dispose_handles_no_async_engine(self, mock_event, mock_create_engine, mock_create_async, mock_asyncio, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_create_async.return_value = MagicMock()

        db = DatabaseEngine(config=db_config)
        db._async_engine = None
        db.dispose()

        mock_engine.dispose.assert_called_once()
        mock_asyncio.run.assert_not_called()

    @patch("gemini.db.core.engine.asyncio")
    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_dispose_handles_no_sync_engine(self, mock_event, mock_create_engine, mock_create_async, mock_asyncio, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_async_engine = MagicMock()
        mock_create_async.return_value = mock_async_engine

        db = DatabaseEngine(config=db_config)
        db._engine = None
        db.dispose()

        mock_engine.dispose.assert_not_called()
        mock_asyncio.run.assert_called_once()


class TestGetEngine:
    """Tests for get_engine method."""

    @patch("gemini.db.core.engine.create_async_engine")
    @patch("gemini.db.core.engine.create_engine")
    @patch("gemini.db.core.engine.event")
    def test_get_engine_returns_engine(self, mock_event, mock_create_engine, mock_create_async, db_config):
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_create_async.return_value = MagicMock()

        db = DatabaseEngine(config=db_config)
        assert db.get_engine() is mock_engine
