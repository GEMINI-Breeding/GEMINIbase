"""Tests for logger configuration classes."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from gemini.logger.config.logger_config import (
    LoggerConfig,
    LocalLoggerConfig,
    RedisLoggerConfig,
)
from gemini.logger.exceptions import LoggerConfigurationError


# ── LoggerConfig (base) ───────────────────────────────────────────


class TestLoggerConfig:
    def test_requires_provider(self):
        with pytest.raises(ValidationError):
            LoggerConfig()

    def test_defaults(self):
        cfg = LoggerConfig(provider="test")
        assert cfg.level == "INFO"
        assert "%(asctime)s" in cfg.format
        assert cfg.buffer_size is None
        assert cfg.extra_fields is None

    def test_forbids_extra_fields(self):
        with pytest.raises(ValidationError):
            LoggerConfig(provider="test", unknown="bad")


# ── LocalLoggerConfig ─────────────────────────────────────────────


class TestLocalLoggerConfig:
    def test_defaults(self, tmp_path):
        cfg = LocalLoggerConfig(log_dir=tmp_path)
        assert cfg.provider == "local"
        assert cfg.filename_template == "{name}_{date}.log"
        assert cfg.backup_count == 5
        assert cfg.max_size_mb is None
        assert cfg.rotation_time is None
        assert cfg.encoding == "utf-8"

    def test_requires_log_dir(self):
        with pytest.raises(ValidationError):
            LocalLoggerConfig()

    def test_resolves_log_dir(self, tmp_path):
        cfg = LocalLoggerConfig(log_dir=tmp_path / "a" / ".." / "b")
        assert ".." not in str(cfg.log_dir)

    def test_rejects_both_rotation_types(self, tmp_path):
        with pytest.raises((ValidationError, LoggerConfigurationError)):
            LocalLoggerConfig(
                log_dir=tmp_path, max_size_mb=10, rotation_time="midnight"
            )

    def test_provider_is_frozen_after_creation(self, tmp_path):
        cfg = LocalLoggerConfig(log_dir=tmp_path)
        with pytest.raises(ValidationError):
            cfg.provider = "other"

    def test_max_size_mb_must_be_positive(self, tmp_path):
        with pytest.raises(ValidationError):
            LocalLoggerConfig(log_dir=tmp_path, max_size_mb=0)

    def test_backup_count_non_negative(self, tmp_path):
        cfg = LocalLoggerConfig(log_dir=tmp_path, backup_count=0)
        assert cfg.backup_count == 0
        with pytest.raises(ValidationError):
            LocalLoggerConfig(log_dir=tmp_path, backup_count=-1)


# ── RedisLoggerConfig ─────────────────────────────────────────────


class TestRedisLoggerConfig:
    def test_defaults(self):
        cfg = RedisLoggerConfig(host="localhost")
        assert cfg.provider == "redis"
        assert cfg.port == 6379
        assert cfg.db == 0
        assert cfg.password is None
        assert cfg.key_prefix == "logs:"
        assert cfg.max_entries is None
        assert cfg.ttl_days is None
        assert cfg.use_ssl is False

    def test_requires_host(self):
        with pytest.raises(ValidationError):
            RedisLoggerConfig()

    def test_rejects_empty_host(self):
        with pytest.raises((ValidationError, LoggerConfigurationError)):
            RedisLoggerConfig(host="")

    def test_rejects_both_retention_strategies(self):
        with pytest.raises((ValidationError, LoggerConfigurationError)):
            RedisLoggerConfig(host="localhost", max_entries=100, ttl_days=7)

    def test_provider_is_frozen_after_creation(self):
        cfg = RedisLoggerConfig(host="localhost")
        with pytest.raises(ValidationError):
            cfg.provider = "other"

    def test_db_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            RedisLoggerConfig(host="localhost", db=-1)

    def test_max_entries_must_be_positive(self):
        with pytest.raises(ValidationError):
            RedisLoggerConfig(host="localhost", max_entries=0)

    def test_ttl_days_must_be_positive(self):
        with pytest.raises(ValidationError):
            RedisLoggerConfig(host="localhost", ttl_days=0)

    def test_custom_config(self):
        cfg = RedisLoggerConfig(
            host="redis.example.com",
            port=6380,
            db=1,
            password="secret",
            key_prefix="myapp:",
            max_entries=1000,
            use_ssl=True,
        )
        assert cfg.port == 6380
        assert cfg.db == 1
        assert cfg.key_prefix == "myapp:"
        assert cfg.use_ssl is True
