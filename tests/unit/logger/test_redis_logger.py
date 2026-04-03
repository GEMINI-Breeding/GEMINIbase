"""Tests for RedisLogger provider."""

import json
import sys
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, call

from gemini.logger.config.logger_config import RedisLoggerConfig
from gemini.logger.interfaces.logger_provider import LogLevel
from gemini.logger.exceptions import (
    LoggerConnectionError,
    LoggerWriteError,
    LoggerInitializationError,
    LoggerAuthError,
)


# Use the redis exception classes from conftest.py (already set up in sys.modules)
_redis_mod = sys.modules["redis"]
_RedisConnectionError = _redis_mod.exceptions.ConnectionError
_RedisAuthenticationError = _redis_mod.exceptions.AuthenticationError

from gemini.logger.providers.redis_logger import RedisLogger


@pytest.fixture
def redis_config():
    return RedisLoggerConfig(host="localhost", port=6379, password="pass")


@pytest.fixture
def logger(redis_config):
    lg = RedisLogger(redis_config)
    # Set up a mock redis client
    lg.redis_client = MagicMock()
    lg.redis_client.pipeline.return_value = MagicMock()
    return lg


# ── __init__ ──────────────────────────────────────────────────────


class TestInit:
    def test_sets_config_and_initial_state(self, redis_config):
        lg = RedisLogger(redis_config)
        assert lg.config is redis_config
        assert lg.redis_client is None
        assert lg._buffer == []


# ── initialize ────────────────────────────────────────────────────


class TestInitialize:
    def test_creates_redis_client_and_pings(self, redis_config):
        mock_client = MagicMock()
        _redis_mod.Redis.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.exists.return_value = False
        mock_client.zadd.return_value = 1

        lg = RedisLogger(redis_config)
        result = lg.initialize()
        assert result is True
        mock_client.ping.assert_called_once()

    def test_raises_on_auth_error(self, redis_config):
        mock_client = MagicMock()
        _redis_mod.Redis.return_value = mock_client
        mock_client.ping.side_effect = _RedisAuthenticationError("bad creds")

        lg = RedisLogger(redis_config)
        with pytest.raises(LoggerAuthError):
            lg.initialize()

    def test_raises_on_connection_error(self, redis_config):
        mock_client = MagicMock()
        _redis_mod.Redis.return_value = mock_client
        mock_client.ping.side_effect = _RedisConnectionError("refused")

        lg = RedisLogger(redis_config)
        with pytest.raises(LoggerConnectionError):
            lg.initialize()


# ── log ───────────────────────────────────────────────────────────


class TestLog:
    def test_writes_entry_directly_without_buffer(self, logger):
        pipe = logger.redis_client.pipeline.return_value
        result = logger.log(LogLevel.INFO, "test message")
        assert result is True
        pipe.set.assert_called_once()
        pipe.zadd.assert_called_once()
        pipe.execute.assert_called_once()

    def test_converts_loglevel_enum_to_string(self, logger):
        pipe = logger.redis_client.pipeline.return_value
        logger.log(LogLevel.ERROR, "err")
        # Verify the entry stored contains string level
        set_call = pipe.set.call_args
        entry = json.loads(set_call[0][1])
        assert entry["level"] == "ERROR"

    def test_buffers_when_buffer_size_set(self):
        config = RedisLoggerConfig(host="localhost", buffer_size=5)
        lg = RedisLogger(config)
        lg.redis_client = MagicMock()
        lg.log(LogLevel.INFO, "msg")
        assert len(lg._buffer) == 1
        lg.redis_client.pipeline.assert_not_called()

    def test_auto_flushes_when_buffer_full(self):
        config = RedisLoggerConfig(host="localhost", buffer_size=2)
        lg = RedisLogger(config)
        lg.redis_client = MagicMock()
        lg.redis_client.pipeline.return_value = MagicMock()
        lg.log(LogLevel.INFO, "msg1")
        lg.log(LogLevel.INFO, "msg2")  # triggers flush
        assert len(lg._buffer) == 0

    def test_sets_ttl_when_configured(self):
        config = RedisLoggerConfig(host="localhost", ttl_days=7)
        lg = RedisLogger(config)
        lg.redis_client = MagicMock()
        pipe = MagicMock()
        lg.redis_client.pipeline.return_value = pipe
        lg.log(LogLevel.INFO, "ttl msg")
        pipe.expire.assert_called_once()

    def test_enforces_max_entries(self):
        config = RedisLoggerConfig(host="localhost", max_entries=100)
        lg = RedisLogger(config)
        lg.redis_client = MagicMock()
        lg.redis_client.zcard.return_value = 101
        lg.redis_client.zrange.return_value = ["old_key"]
        pipe = MagicMock()
        lg.redis_client.pipeline.return_value = pipe
        lg.log(LogLevel.INFO, "msg")
        pipe.delete.assert_called()
        pipe.zremrangebyrank.assert_called()


# ── convenience methods ───────────────────────────────────────────


class TestConvenienceMethods:
    def test_debug(self, logger):
        assert logger.debug("d") is True

    def test_info(self, logger):
        assert logger.info("i") is True

    def test_warning(self, logger):
        assert logger.warning("w") is True

    def test_error(self, logger):
        assert logger.error("e") is True

    def test_critical(self, logger):
        assert logger.critical("c") is True


# ── flush ─────────────────────────────────────────────────────────


class TestFlush:
    def test_empty_buffer_returns_true(self, logger):
        assert logger.flush() is True

    def test_flushes_buffered_entries(self):
        config = RedisLoggerConfig(host="localhost", buffer_size=10)
        lg = RedisLogger(config)
        lg.redis_client = MagicMock()
        pipe = MagicMock()
        lg.redis_client.pipeline.return_value = pipe
        lg.log(LogLevel.INFO, "a")
        lg.log(LogLevel.INFO, "b")
        assert len(lg._buffer) == 2
        lg.flush()
        assert len(lg._buffer) == 0
        pipe.execute.assert_called_once()


# ── rotate ────────────────────────────────────────────────────────


class TestRotate:
    def test_always_returns_true(self, logger):
        assert logger.rotate() is True


# ── get_logs ──────────────────────────────────────────────────────


class TestGetLogs:
    def test_retrieves_entries(self, logger):
        entry = {"level": "INFO", "message": "hello", "timestamp": "2025-01-01T00:00:00"}
        logger.redis_client.zrangebyscore.return_value = ["key1"]
        pipe = MagicMock()
        pipe.execute.return_value = [json.dumps(entry)]
        logger.redis_client.pipeline.return_value = pipe
        results = list(logger.get_logs())
        assert len(results) == 1
        assert results[0]["message"] == "hello"

    def test_filters_by_level(self, logger):
        entries = [
            json.dumps({"level": "INFO", "message": "a", "timestamp": "2025-01-01T00:00:00"}),
            json.dumps({"level": "ERROR", "message": "b", "timestamp": "2025-01-01T00:01:00"}),
        ]
        logger.redis_client.zrangebyscore.return_value = ["k1", "k2"]
        pipe = MagicMock()
        pipe.execute.return_value = entries
        logger.redis_client.pipeline.return_value = pipe
        results = list(logger.get_logs(level="ERROR"))
        assert len(results) == 1
        assert results[0]["message"] == "b"

    def test_respects_limit(self, logger):
        entries = [
            json.dumps({"level": "INFO", "message": f"m{i}", "timestamp": "2025-01-01T00:00:00"})
            for i in range(5)
        ]
        logger.redis_client.zrangebyscore.return_value = [f"k{i}" for i in range(5)]
        pipe = MagicMock()
        pipe.execute.return_value = entries
        logger.redis_client.pipeline.return_value = pipe
        results = list(logger.get_logs(limit=2))
        assert len(results) == 2

    def test_returns_empty_when_no_keys(self, logger):
        logger.redis_client.zrangebyscore.return_value = []
        results = list(logger.get_logs())
        assert results == []

    def test_skips_malformed_entries(self, logger):
        logger.redis_client.zrangebyscore.return_value = ["k1"]
        pipe = MagicMock()
        pipe.execute.return_value = ["not json"]
        logger.redis_client.pipeline.return_value = pipe
        results = list(logger.get_logs())
        assert results == []

    def test_skips_none_entries(self, logger):
        logger.redis_client.zrangebyscore.return_value = ["k1"]
        pipe = MagicMock()
        pipe.execute.return_value = [None]
        logger.redis_client.pipeline.return_value = pipe
        results = list(logger.get_logs())
        assert results == []


# ── clear_logs ────────────────────────────────────────────────────


class TestClearLogs:
    def test_clears_older_than(self, logger):
        logger.redis_client.zrangebyscore.return_value = ["old_key"]
        pipe = MagicMock()
        logger.redis_client.pipeline.return_value = pipe
        result = logger.clear_logs(older_than=datetime(2024, 1, 1))
        assert result is True
        pipe.delete.assert_called_once_with("old_key")
        pipe.zremrangebyscore.assert_called_once()

    def test_clears_by_level(self, logger):
        logger.redis_client.zrange.return_value = ["k1", "k2"]
        logger.redis_client.get.side_effect = [
            json.dumps({"level": "INFO", "message": "a"}),
            json.dumps({"level": "ERROR", "message": "b"}),
        ]
        pipe = MagicMock()
        logger.redis_client.pipeline.return_value = pipe
        result = logger.clear_logs(level="ERROR")
        assert result is True
        pipe.delete.assert_called_once_with("k2")
        pipe.zrem.assert_called_once()

    def test_returns_true_with_no_criteria(self, logger):
        pipe = MagicMock()
        logger.redis_client.pipeline.return_value = pipe
        assert logger.clear_logs() is True


# ── _format_extra ─────────────────────────────────────────────────


class TestFormatExtra:
    def test_combines_fields(self):
        config = RedisLoggerConfig(
            host="localhost", extra_fields={"env": "test"}
        )
        lg = RedisLogger(config)
        result = lg._format_extra({"req": "123"})
        assert result["env"] == "test"
        assert result["req"] == "123"

    def test_returns_config_fields_when_no_extra(self):
        config = RedisLoggerConfig(
            host="localhost", extra_fields={"env": "prod"}
        )
        lg = RedisLogger(config)
        result = lg._format_extra()
        assert result == {"env": "prod"}


# ── _generate_log_key ─────────────────────────────────────────────


class TestGenerateLogKey:
    def test_uses_prefix_and_timestamp(self, redis_config):
        lg = RedisLogger(redis_config)
        ts = datetime(2025, 6, 15, 12, 0, 0)
        key = lg._generate_log_key(ts)
        assert key.startswith("logs:")
        assert "2025-06-15" in key
