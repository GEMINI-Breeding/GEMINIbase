"""Tests for gemini.config.settings.GEMINISettings."""
import os
import tempfile
import pytest
from unittest.mock import patch

from gemini.config.settings import GEMINISettings


class TestGEMINISettingsDefaults:
    """Verify default field values on a fresh GEMINISettings instance."""

    def test_meta_defaults(self):
        s = GEMINISettings()
        # GEMINI_DEBUG may come from env; just check type
        assert isinstance(s.GEMINI_DEBUG, bool)
        assert isinstance(s.GEMINI_TYPE, str)
        assert isinstance(s.GEMINI_PUBLIC_DOMAIN, str)
        assert isinstance(s.GEMINI_PUBLIC_IP, str)

    def test_db_defaults(self):
        s = GEMINISettings()
        assert s.GEMINI_DB_CONTAINER_NAME == "gemini-db"
        assert s.GEMINI_DB_IMAGE_NAME == "gemini/db"
        assert s.GEMINI_DB_PORT == 5432

    def test_logger_defaults(self):
        s = GEMINISettings()
        assert s.GEMINI_LOGGER_CONTAINER_NAME == "gemini-logger"
        assert s.GEMINI_LOGGER_IMAGE_NAME == "gemini/logger"
        assert s.GEMINI_LOGGER_PORT == 6379

    def test_storage_defaults(self):
        s = GEMINISettings()
        assert s.GEMINI_STORAGE_CONTAINER_NAME == "gemini-storage"
        assert s.GEMINI_STORAGE_IMAGE_NAME == "gemini/storage"
        assert s.GEMINI_STORAGE_PORT == 9000
        assert s.GEMINI_STORAGE_API_PORT == 9001
        assert s.GEMINI_STORAGE_BUCKET_NAME is not None

    def test_rest_api_defaults(self):
        s = GEMINISettings()
        assert s.GEMINI_REST_API_CONTAINER_NAME == "gemini-rest-api"
        assert s.GEMINI_REST_API_IMAGE_NAME == "gemini/rest-api"
        assert s.GEMINI_REST_API_PORT == 7777

    def test_scheduler_db_defaults(self):
        s = GEMINISettings()
        assert s.GEMINI_SCHEDULER_DB_CONTAINER_NAME == "gemini-scheduler-db"
        assert s.GEMINI_SCHEDULER_DB_IMAGE_NAME == "gemini/scheduler-db"
        assert s.GEMINI_SCHEDULER_DB_PORT == 6432

    def test_scheduler_server_defaults(self):
        s = GEMINISettings()
        assert s.GEMINI_SCHEDULER_SERVER_CONTAINER_NAME == "gemini-scheduler-server"
        assert s.GEMINI_SCHEDULER_SERVER_IMAGE_NAME == "gemini/scheduler-server"
        assert s.GEMINI_SCHEDULER_SERVER_PORT == 4200

    def test_reverse_proxy_defaults(self):
        s = GEMINISettings()
        assert s.GEMINI_REVERSE_PROXY_CONTAINER_NAME == "gemini-reverse-proxy"
        assert s.GEMINI_REVERSE_PROXY_IMAGE_NAME == "gemini/reverse-proxy"
        assert s.GEMINI_REVERSE_PROXY_HOSTNAME == "gemini-reverse-proxy"


class TestApplyType:
    """Tests for apply_type() which adjusts hostnames based on deployment mode."""

    def test_apply_type_local_sets_localhost(self):
        s = GEMINISettings()
        s.apply_type("local")
        assert os.environ["GEMINI_DB_HOSTNAME"] == "localhost"
        assert os.environ["GEMINI_LOGGER_HOSTNAME"] == "localhost"
        assert os.environ["GEMINI_STORAGE_HOSTNAME"] == "localhost"
        assert os.environ["GEMINI_REST_API_HOSTNAME"] == "localhost"
        assert os.environ["GEMINI_SCHEDULER_DB_HOSTNAME"] == "localhost"
        assert os.environ["GEMINI_SCHEDULER_SERVER_HOSTNAME"] == "localhost"

    def test_apply_type_public_calls_set_public_ip(self):
        with patch.object(GEMINISettings, "set_public_ip") as mock_set_ip:
            s = GEMINISettings()
            s.apply_type("public")
            mock_set_ip.assert_called_with(s.GEMINI_PUBLIC_IP)

    def test_apply_type_internal_does_nothing(self):
        """Internal type should not change hostnames."""
        s = GEMINISettings()
        original_db_host = os.environ.get("GEMINI_DB_HOSTNAME")
        s.apply_type("internal")
        # The value shouldn't be forcefully changed
        assert os.environ.get("GEMINI_DB_HOSTNAME") == original_db_host


class TestSetSetting:
    """Tests for set_setting()."""

    def test_set_setting_updates_value_and_env(self):
        s = GEMINISettings()
        s.set_setting("GEMINI_DB_PORT", 9999)
        assert s.GEMINI_DB_PORT == 9999
        assert os.environ["GEMINI_DB_PORT"] == "9999"
        # Restore for other tests
        os.environ["GEMINI_DB_PORT"] = "5432"

    def test_set_setting_updates_string_value(self):
        s = GEMINISettings()
        s.set_setting("GEMINI_DB_USER", "new_user")
        assert s.GEMINI_DB_USER == "new_user"
        assert os.environ["GEMINI_DB_USER"] == "new_user"

    def test_set_setting_raises_key_error_for_invalid_key(self):
        s = GEMINISettings()
        with pytest.raises(KeyError, match="does not exist"):
            s.set_setting("NONEXISTENT_KEY", "value")

    def test_set_setting_raises_key_error_for_empty_key(self):
        s = GEMINISettings()
        with pytest.raises(KeyError):
            s.set_setting("", "value")


class TestEnvFile:
    """Tests for create_env_file() and from_env_file()."""

    def test_create_and_read_env_file(self):
        s = GEMINISettings()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            path = f.name
        try:
            result_path = s.create_env_file(path)
            assert result_path == path
            assert os.path.exists(path)

            loaded = GEMINISettings.from_env_file(path)
            assert loaded.GEMINI_DB_CONTAINER_NAME == s.GEMINI_DB_CONTAINER_NAME
            assert loaded.GEMINI_LOGGER_PORT == s.GEMINI_LOGGER_PORT
            assert loaded.GEMINI_STORAGE_CONTAINER_NAME == s.GEMINI_STORAGE_CONTAINER_NAME
        finally:
            os.unlink(path)

    def test_create_env_file_writes_all_fields(self):
        s = GEMINISettings()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            path = f.name
        try:
            s.create_env_file(path)
            with open(path) as f:
                content = f.read()
            # Spot-check that key fields are present
            assert "GEMINI_DB_PORT=" in content
            assert "GEMINI_STORAGE_BUCKET_NAME=" in content
            assert "GEMINI_SCHEDULER_SERVER_PORT=" in content
        finally:
            os.unlink(path)

    def test_from_env_file_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            GEMINISettings.from_env_file("/nonexistent/path/.env")


class TestSetLocalAndDebug:
    """Tests for set_local() and set_debug() convenience methods."""

    def test_set_local_sets_all_hostnames_to_localhost(self):
        s = GEMINISettings()
        s.set_local()
        assert os.environ["GEMINI_DB_HOSTNAME"] == "localhost"
        assert os.environ["GEMINI_LOGGER_HOSTNAME"] == "localhost"
        assert os.environ["GEMINI_STORAGE_HOSTNAME"] == "localhost"
        assert os.environ["GEMINI_REST_API_HOSTNAME"] == "localhost"
        assert os.environ["GEMINI_SCHEDULER_DB_HOSTNAME"] == "localhost"
        assert os.environ["GEMINI_SCHEDULER_SERVER_HOSTNAME"] == "localhost"

    def test_set_debug_true(self):
        s = GEMINISettings()
        s.set_debug(True)
        assert os.environ["GEMINI_DEBUG"] == "True"

    def test_set_debug_false(self):
        s = GEMINISettings()
        s.set_debug(False)
        assert os.environ["GEMINI_DEBUG"] == "False"

    def test_set_public_domain(self):
        s = GEMINISettings()
        s.set_public_domain("example.com")
        assert os.environ["GEMINI_DB_HOSTNAME"] == "example.com"
        assert os.environ["GEMINI_LOGGER_HOSTNAME"] == "example.com"
        # Restore
        s.set_local()

    def test_set_public_ip(self):
        s = GEMINISettings()
        s.set_public_ip("10.0.0.1")
        assert os.environ["GEMINI_DB_HOSTNAME"] == "10.0.0.1"
        assert os.environ["GEMINI_STORAGE_HOSTNAME"] == "10.0.0.1"
        # Restore
        s.set_local()
