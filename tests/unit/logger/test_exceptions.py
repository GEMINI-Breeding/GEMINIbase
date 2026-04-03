"""Tests for logger exception hierarchy."""

import pytest
from gemini.logger.exceptions import (
    LoggerError,
    LoggerConnectionError,
    LoggerAuthError,
    LoggerInitializationError,
    LoggerConfigurationError,
    LoggerWriteError,
    LoggerReadError,
    LoggerFlushError,
    LoggerRotationError,
)


class TestExceptionHierarchy:
    """Verify every custom exception exists and inherits from LoggerError."""

    @pytest.mark.parametrize(
        "exc_class",
        [
            LoggerConnectionError,
            LoggerAuthError,
            LoggerInitializationError,
            LoggerConfigurationError,
            LoggerWriteError,
            LoggerReadError,
            LoggerFlushError,
            LoggerRotationError,
        ],
    )
    def test_inherits_from_logger_error(self, exc_class):
        assert issubclass(exc_class, LoggerError)

    def test_logger_error_inherits_from_exception(self):
        assert issubclass(LoggerError, Exception)

    @pytest.mark.parametrize(
        "exc_class",
        [
            LoggerError,
            LoggerConnectionError,
            LoggerAuthError,
            LoggerInitializationError,
            LoggerConfigurationError,
            LoggerWriteError,
            LoggerReadError,
            LoggerFlushError,
            LoggerRotationError,
        ],
    )
    def test_can_be_raised_and_caught(self, exc_class):
        with pytest.raises(exc_class):
            raise exc_class("test message")

    @pytest.mark.parametrize(
        "exc_class",
        [
            LoggerError,
            LoggerConnectionError,
            LoggerAuthError,
            LoggerInitializationError,
            LoggerConfigurationError,
            LoggerWriteError,
            LoggerReadError,
            LoggerFlushError,
            LoggerRotationError,
        ],
    )
    def test_message_preserved(self, exc_class):
        err = exc_class("specific message")
        assert str(err) == "specific message"

    def test_all_subclasses_caught_by_logger_error(self):
        for cls in [
            LoggerConnectionError,
            LoggerAuthError,
            LoggerInitializationError,
            LoggerConfigurationError,
            LoggerWriteError,
            LoggerReadError,
            LoggerFlushError,
            LoggerRotationError,
        ]:
            with pytest.raises(LoggerError):
                raise cls("caught by base")
