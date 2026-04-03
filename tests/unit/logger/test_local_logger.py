"""Tests for LocalLogger provider."""

import json
import logging
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

from gemini.logger.providers.local_logger import LocalLogger
from gemini.logger.config.logger_config import LocalLoggerConfig
from gemini.logger.interfaces.logger_provider import LogLevel
from gemini.logger.exceptions import (
    LoggerInitializationError,
    LoggerWriteError,
    LoggerRotationError,
)


@pytest.fixture
def local_config(tmp_path):
    return LocalLoggerConfig(log_dir=tmp_path / "logs")


@pytest.fixture
def logger(local_config):
    lg = LocalLogger(local_config)
    lg.initialize()
    return lg


# ── __init__ ──────────────────────────────────────────────────────


class TestInit:
    def test_sets_config_and_initial_state(self, local_config):
        lg = LocalLogger(local_config)
        assert lg.config is local_config
        assert lg.logger is None
        assert lg._buffer == []


# ── initialize ────────────────────────────────────────────────────


class TestInitialize:
    def test_creates_log_directory(self, tmp_path):
        log_dir = tmp_path / "new_logs"
        config = LocalLoggerConfig(log_dir=log_dir)
        lg = LocalLogger(config)
        lg.initialize()
        assert log_dir.exists()

    def test_returns_true(self, local_config):
        lg = LocalLogger(local_config)
        assert lg.initialize() is True

    def test_creates_logger_with_handler(self, logger):
        assert logger.logger is not None
        assert len(logger.logger.handlers) >= 1

    def test_timed_rotation_handler(self, tmp_path):
        config = LocalLoggerConfig(
            log_dir=tmp_path / "timed", rotation_time="midnight"
        )
        lg = LocalLogger(config)
        lg.initialize()
        from logging.handlers import TimedRotatingFileHandler

        assert any(
            isinstance(h, TimedRotatingFileHandler) for h in lg.logger.handlers
        )

    def test_size_rotation_handler(self, tmp_path):
        config = LocalLoggerConfig(
            log_dir=tmp_path / "sized", max_size_mb=10
        )
        lg = LocalLogger(config)
        lg.initialize()
        from logging.handlers import RotatingFileHandler

        assert any(
            isinstance(h, RotatingFileHandler) for h in lg.logger.handlers
        )

    def test_plain_file_handler_when_no_rotation(self, tmp_path):
        config = LocalLoggerConfig(log_dir=tmp_path / "plain")
        lg = LocalLogger(config)
        lg.initialize()
        assert any(
            isinstance(h, logging.FileHandler) for h in lg.logger.handlers
        )


# ── log / convenience methods ─────────────────────────────────────


class TestLog:
    def test_log_with_loglevel_enum(self, logger):
        assert logger.log(LogLevel.INFO, "test message") is True

    def test_log_with_string_level(self, logger):
        assert logger.log("INFO", "string level") is True

    def test_debug(self, logger):
        assert logger.debug("debug msg") is True

    def test_info(self, logger):
        assert logger.info("info msg") is True

    def test_warning(self, logger):
        assert logger.warning("warn msg") is True

    def test_error(self, logger):
        assert logger.error("err msg") is True

    def test_critical(self, logger):
        assert logger.critical("crit msg") is True


# ── buffering ─────────────────────────────────────────────────────


class TestBuffering:
    def test_buffers_when_buffer_size_set(self, tmp_path):
        config = LocalLoggerConfig(log_dir=tmp_path / "buf", buffer_size=5)
        lg = LocalLogger(config)
        lg.initialize()
        lg.log(LogLevel.INFO, "msg1")
        assert len(lg._buffer) == 1

    def test_auto_flushes_when_buffer_full(self, tmp_path):
        config = LocalLoggerConfig(log_dir=tmp_path / "buf", buffer_size=2)
        lg = LocalLogger(config)
        lg.initialize()
        lg.log(LogLevel.INFO, "msg1")
        lg.log(LogLevel.INFO, "msg2")  # Should trigger flush
        assert len(lg._buffer) == 0


# ── flush ─────────────────────────────────────────────────────────


class TestFlush:
    def test_flush_empty_buffer_returns_true(self, logger):
        assert logger.flush() is True

    def test_flush_clears_buffer(self, tmp_path):
        config = LocalLoggerConfig(log_dir=tmp_path / "flush", buffer_size=10)
        lg = LocalLogger(config)
        lg.initialize()
        lg.log(LogLevel.INFO, "buffered")
        assert len(lg._buffer) == 1
        lg.flush()
        assert len(lg._buffer) == 0


# ── rotate ────────────────────────────────────────────────────────


class TestRotate:
    def test_rotate_returns_true(self, logger):
        assert logger.rotate() is True

    def test_rotate_returns_true_on_rotating_handler(self, tmp_path):
        config = LocalLoggerConfig(
            log_dir=tmp_path / "rot", max_size_mb=1
        )
        lg = LocalLogger(config)
        lg.initialize()
        result = lg.rotate()
        assert result is True


# ── get_logs ──────────────────────────────────────────────────────


class TestGetLogs:
    def test_reads_json_log_entries(self, tmp_path):
        log_dir = tmp_path / "read"
        log_dir.mkdir()
        log_file = log_dir / "test.log"
        entries = [
            {"level": "INFO", "message": "hello", "timestamp": "2025-01-01T00:00:00"},
            {"level": "ERROR", "message": "oops", "timestamp": "2025-01-01T00:01:00"},
        ]
        log_file.write_text("\n".join(json.dumps(e) for e in entries))
        config = LocalLoggerConfig(log_dir=log_dir)
        lg = LocalLogger(config)
        lg.initialize()
        results = list(lg.get_logs())
        assert len(results) == 2

    def test_filters_by_level(self, tmp_path):
        log_dir = tmp_path / "filter"
        log_dir.mkdir()
        log_file = log_dir / "test.log"
        entries = [
            {"level": "INFO", "message": "a", "timestamp": "2025-01-01T00:00:00"},
            {"level": "ERROR", "message": "b", "timestamp": "2025-01-01T00:01:00"},
        ]
        log_file.write_text("\n".join(json.dumps(e) for e in entries))
        config = LocalLoggerConfig(log_dir=log_dir)
        lg = LocalLogger(config)
        lg.initialize()
        results = list(lg.get_logs(level="ERROR"))
        assert len(results) == 1
        assert results[0]["message"] == "b"

    def test_limit_parameter(self, tmp_path):
        log_dir = tmp_path / "limit"
        log_dir.mkdir()
        log_file = log_dir / "test.log"
        entries = [
            {"level": "INFO", "message": f"m{i}", "timestamp": "2025-01-01T00:00:00"}
            for i in range(5)
        ]
        log_file.write_text("\n".join(json.dumps(e) for e in entries))
        config = LocalLoggerConfig(log_dir=log_dir)
        lg = LocalLogger(config)
        lg.initialize()
        results = list(lg.get_logs(limit=2))
        assert len(results) == 2

    def test_skips_malformed_lines(self, tmp_path):
        log_dir = tmp_path / "malformed"
        log_dir.mkdir()
        log_file = log_dir / "test.log"
        log_file.write_text("not json\n" + json.dumps({"level": "INFO", "message": "ok", "timestamp": "2025-01-01T00:00:00"}))
        config = LocalLoggerConfig(log_dir=log_dir)
        lg = LocalLogger(config)
        lg.initialize()
        results = list(lg.get_logs())
        assert len(results) == 1


# ── clear_logs ────────────────────────────────────────────────────


class TestClearLogs:
    def test_clears_old_logs(self, tmp_path):
        log_dir = tmp_path / "clear"
        log_dir.mkdir()
        old_file = log_dir / "app_20200101.log"
        new_file = log_dir / "app_20250101.log"
        old_file.write_text("old")
        new_file.write_text("new")
        config = LocalLoggerConfig(log_dir=log_dir)
        lg = LocalLogger(config)
        lg.initialize()
        lg.clear_logs(older_than=datetime(2024, 1, 1))
        assert not old_file.exists()
        assert new_file.exists()

    def test_returns_true(self, logger):
        assert logger.clear_logs() is True


# ── _format_extra ─────────────────────────────────────────────────


class TestFormatExtra:
    def test_combines_config_and_extra(self, tmp_path):
        config = LocalLoggerConfig(
            log_dir=tmp_path / "extra",
            extra_fields={"app": "gemini"},
        )
        lg = LocalLogger(config)
        result = lg._format_extra({"request_id": "123"})
        assert result["app"] == "gemini"
        assert result["request_id"] == "123"

    def test_returns_config_fields_when_no_extra(self, tmp_path):
        config = LocalLoggerConfig(
            log_dir=tmp_path / "extra2",
            extra_fields={"app": "gemini"},
        )
        lg = LocalLogger(config)
        result = lg._format_extra()
        assert result == {"app": "gemini"}
