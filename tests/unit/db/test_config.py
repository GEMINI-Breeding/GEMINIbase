"""
Tests for gemini.db.config.DatabaseConfig.
"""
import pytest
from sqlalchemy.pool import QueuePool, AsyncAdaptedQueuePool

from gemini.db.config import DatabaseConfig


class TestDatabaseConfig:
    """Tests for DatabaseConfig validation and defaults."""

    def test_valid_url(self):
        config = DatabaseConfig(database_url="postgresql://user:pass@localhost/db")
        assert config.database_url == "postgresql://user:pass@localhost/db"

    def test_empty_url_raises(self):
        with pytest.raises(ValueError, match="Database URL must be provided"):
            DatabaseConfig(database_url="")

    def test_none_url_raises(self):
        with pytest.raises(ValueError):
            DatabaseConfig(database_url=None)

    def test_default_pool_size(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d")
        assert config.pool_size == 10

    def test_default_max_overflow(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d")
        assert config.max_overflow == 20

    def test_default_pool_timeout(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d")
        assert config.pool_timeout == 30

    def test_default_pool_recycle(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d")
        assert config.pool_recycle == 1800

    def test_default_echo_sql(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d")
        assert config.echo_sql is False

    def test_default_echo_pool(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d")
        assert config.echo_pool is False

    def test_default_pool_class(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d")
        assert config.pool_class is QueuePool

    def test_default_async_pool_class(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d")
        assert config.async_pool_class is AsyncAdaptedQueuePool

    def test_default_isolation_level(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d")
        assert config.isolation_level == "READ COMMITTED"

    def test_custom_pool_size(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d", pool_size=50)
        assert config.pool_size == 50

    def test_custom_max_overflow(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d", max_overflow=100)
        assert config.max_overflow == 100

    def test_custom_pool_timeout(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d", pool_timeout=60)
        assert config.pool_timeout == 60

    def test_custom_pool_recycle(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d", pool_recycle=3600)
        assert config.pool_recycle == 3600

    def test_custom_echo_sql(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d", echo_sql=True)
        assert config.echo_sql is True

    def test_custom_echo_pool(self):
        config = DatabaseConfig(database_url="postgresql://u:p@h/d", echo_pool=True)
        assert config.echo_pool is True

    def test_custom_isolation_level(self):
        config = DatabaseConfig(
            database_url="postgresql://u:p@h/d",
            isolation_level="SERIALIZABLE",
        )
        assert config.isolation_level == "SERIALIZABLE"

    def test_multiple_custom_values(self):
        config = DatabaseConfig(
            database_url="postgresql://u:p@h/d",
            pool_size=5,
            max_overflow=10,
            pool_timeout=15,
            pool_recycle=900,
            echo_sql=True,
        )
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.pool_timeout == 15
        assert config.pool_recycle == 900
        assert config.echo_sql is True
