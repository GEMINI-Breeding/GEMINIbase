"""Tests for LoggerFactory."""

import pytest
from unittest.mock import MagicMock, patch

from gemini.logger.factory.logger_factory import LoggerFactory
from gemini.logger.config.logger_config import (
    LocalLoggerConfig,
    RedisLoggerConfig,
)
from gemini.logger.providers.local_logger import LocalLogger
from gemini.logger.providers.redis_logger import RedisLogger
from gemini.logger.exceptions import LoggerInitializationError


@pytest.fixture(autouse=True)
def reset_factory():
    """Reset the singleton and restore the default registry after each test."""
    original_providers = LoggerFactory._providers.copy()
    LoggerFactory.reset_provider()
    yield
    LoggerFactory._providers = original_providers
    LoggerFactory.reset_provider()


# ── Registry ──────────────────────────────────────────────────────


class TestRegistry:
    def test_default_providers_registered(self):
        assert "local" in LoggerFactory._providers
        assert "redis" in LoggerFactory._providers

    def test_register_new_provider(self):
        mock_class = MagicMock()
        LoggerFactory.register_provider("custom", mock_class)
        assert LoggerFactory._providers["custom"] is mock_class

    def test_register_duplicate_raises(self):
        with pytest.raises(ValueError, match="already registered"):
            LoggerFactory.register_provider("local", LocalLogger)


# ── create_provider ───────────────────────────────────────────────


class TestCreateProvider:
    def test_creates_local_provider(self, tmp_path):
        config = LocalLoggerConfig(log_dir=tmp_path / "logs")
        provider = LoggerFactory.create_provider(config)
        assert isinstance(provider, LocalLogger)

    def test_raises_for_unknown_provider(self):
        config = MagicMock()
        config.provider = "unknown"
        with pytest.raises(ValueError, match="Unsupported"):
            LoggerFactory.create_provider(config)

    def test_raises_initialization_error_on_failure(self):
        config = MagicMock()
        config.provider = "local"
        # The LocalLogger constructor will accept a mock config,
        # but initialize() will fail
        with pytest.raises(LoggerInitializationError):
            LoggerFactory.create_provider(config)


# ── get_provider (singleton) ──────────────────────────────────────


class TestGetProvider:
    def test_returns_same_instance(self, tmp_path):
        config = LocalLoggerConfig(log_dir=tmp_path / "logs")
        p1 = LoggerFactory.get_provider(config)
        p2 = LoggerFactory.get_provider(config)
        assert p1 is p2

    def test_raises_without_config(self):
        with pytest.raises(NotImplementedError):
            LoggerFactory.get_provider()

    def test_reset_clears_singleton(self, tmp_path):
        config = LocalLoggerConfig(log_dir=tmp_path / "logs")
        LoggerFactory.get_provider(config)
        LoggerFactory.reset_provider()
        assert LoggerFactory._instance is None
