"""Tests for gemini.manager.GEMINIManager."""
import os
import subprocess
import tempfile
import pytest
from unittest.mock import patch, MagicMock, mock_open

from gemini.manager import GEMINIManager, GEMINIComponentType, GEMINIContainerInfo
from gemini.config.settings import GEMINISettings


class TestScanContainers:
    """Tests for scan_containers()."""

    def test_scan_containers_empty_list(self, mock_docker_client_fixture):
        mock_docker_client_fixture.containers.list.return_value = []
        manager = GEMINIManager()
        assert manager.docker_containers == {}

    def test_scan_containers_with_containers(self, mock_docker_client_fixture):
        mock_container = MagicMock()
        mock_container.attrs = {
            "Name": "/gemini-db",
            "Config": {"Image": "gemini/db"},
            "Id": "abc123",
            "NetworkSettings": {
                "Networks": {
                    "gemini_network": {"IPAddress": "172.18.0.2"}
                }
            },
        }
        mock_docker_client_fixture.containers.list.return_value = [mock_container]
        manager = GEMINIManager()
        assert "gemini-db" in manager.docker_containers
        info = manager.docker_containers["gemini-db"]
        assert info.id == "abc123"
        assert info.image == "gemini/db"
        assert info.ip_address == "172.18.0.2"
        # Reset for other tests
        mock_docker_client_fixture.containers.list.return_value = []

    def test_scan_containers_handles_exception(self, mock_docker_client_fixture, capsys):
        mock_docker_client_fixture.containers.list.side_effect = RuntimeError("Docker not available")
        manager = GEMINIManager()
        captured = capsys.readouterr()
        assert "Error scanning containers" in captured.out
        assert manager.docker_containers == {}
        # Reset
        mock_docker_client_fixture.containers.list.side_effect = None
        mock_docker_client_fixture.containers.list.return_value = []


class TestGetComponentSettings:
    """Tests for get_component_settings()."""

    def test_db_settings(self):
        manager = GEMINIManager()
        result = manager.get_component_settings(GEMINIComponentType.DB)
        expected_keys = {
            "GEMINI_DB_CONTAINER_NAME",
            "GEMINI_DB_IMAGE_NAME",
            "GEMINI_DB_USER",
            "GEMINI_DB_PASSWORD",
            "GEMINI_DB_HOSTNAME",
            "GEMINI_DB_NAME",
            "GEMINI_DB_PORT",
        }
        assert set(result.keys()) == expected_keys

    def test_logger_settings(self):
        manager = GEMINIManager()
        result = manager.get_component_settings(GEMINIComponentType.LOGGER)
        expected_keys = {
            "GEMINI_LOGGER_CONTAINER_NAME",
            "GEMINI_LOGGER_IMAGE_NAME",
            "GEMINI_LOGGER_HOSTNAME",
            "GEMINI_LOGGER_PORT",
            "GEMINI_LOGGER_PASSWORD",
        }
        assert set(result.keys()) == expected_keys

    def test_storage_settings(self):
        manager = GEMINIManager()
        result = manager.get_component_settings(GEMINIComponentType.STORAGE)
        expected_keys = {
            "GEMINI_STORAGE_CONTAINER_NAME",
            "GEMINI_STORAGE_IMAGE_NAME",
            "GEMINI_STORAGE_HOSTNAME",
            "GEMINI_STORAGE_PORT",
            "GEMINI_STORAGE_API_PORT",
            "GEMINI_STORAGE_ROOT_USER",
            "GEMINI_STORAGE_ROOT_PASSWORD",
            "GEMINI_STORAGE_ACCESS_KEY",
            "GEMINI_STORAGE_SECRET_KEY",
            "GEMINI_STORAGE_BUCKET_NAME",
        }
        assert set(result.keys()) == expected_keys

    def test_rest_api_settings(self):
        manager = GEMINIManager()
        result = manager.get_component_settings(GEMINIComponentType.REST_API)
        expected_keys = {
            "GEMINI_REST_API_CONTAINER_NAME",
            "GEMINI_REST_API_IMAGE_NAME",
            "GEMINI_REST_API_HOSTNAME",
            "GEMINI_REST_API_PORT",
        }
        assert set(result.keys()) == expected_keys

    def test_scheduler_db_settings(self):
        manager = GEMINIManager()
        result = manager.get_component_settings(GEMINIComponentType.SCHEDULER_DB)
        expected_keys = {
            "GEMINI_SCHEDULER_DB_CONTAINER_NAME",
            "GEMINI_SCHEDULER_DB_IMAGE_NAME",
            "GEMINI_SCHEDULER_DB_HOSTNAME",
            "GEMINI_SCHEDULER_DB_USER",
            "GEMINI_SCHEDULER_DB_PASSWORD",
            "GEMINI_SCHEDULER_DB_NAME",
            "GEMINI_SCHEDULER_DB_PORT",
        }
        assert set(result.keys()) == expected_keys

    def test_scheduler_server_settings(self):
        manager = GEMINIManager()
        result = manager.get_component_settings(GEMINIComponentType.SCHEDULER_SERVER)
        expected_keys = {
            "GEMINI_SCHEDULER_SERVER_CONTAINER_NAME",
            "GEMINI_SCHEDULER_SERVER_IMAGE_NAME",
            "GEMINI_SCHEDULER_SERVER_HOSTNAME",
            "GEMINI_SCHEDULER_SERVER_PORT",
        }
        assert set(result.keys()) == expected_keys

    def test_meta_settings(self):
        manager = GEMINIManager()
        result = manager.get_component_settings(GEMINIComponentType.META)
        expected_keys = {
            "GEMINI_DEBUG",
            "GEMINI_TYPE",
            "GEMINI_PUBLIC_DOMAIN",
            "GEMINI_PUBLIC_IP",
        }
        assert set(result.keys()) == expected_keys


class TestGetAndSetSettings:
    """Tests for get_settings() and set_setting()."""

    def test_get_settings_returns_settings_instance(self):
        manager = GEMINIManager()
        settings = manager.get_settings()
        assert isinstance(settings, GEMINISettings)

    def test_set_setting_delegates_to_settings(self):
        with patch.object(GEMINIManager, "save_settings"):
            manager = GEMINIManager()
            manager.set_setting("GEMINI_DB_PORT", 1234)
            # The setting was applied (set_setting creates a new GEMINISettings
            # internally, so we verify via env var which is the side effect)
            assert os.environ["GEMINI_DB_PORT"] == "1234"
            # Restore
            os.environ["GEMINI_DB_PORT"] = "5432"

    def test_set_setting_raises_key_error_for_invalid_setting(self):
        manager = GEMINIManager()
        with pytest.raises(KeyError, match="does not exist"):
            manager.set_setting("TOTALLY_FAKE_SETTING", "value")


class TestDockerCommands:
    """Tests for build(), start(), stop(), clean(), rebuild(), update()."""

    @patch("gemini.manager.subprocess.run")
    def test_build_calls_subprocess(self, mock_run):
        manager = GEMINIManager()
        result = manager.build()
        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "build" in args
        assert "docker" in args

    @patch("gemini.manager.subprocess.run")
    def test_build_returns_false_on_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        manager = GEMINIManager()
        result = manager.build()
        assert result is False

    @patch("gemini.manager.subprocess.run")
    def test_start_calls_subprocess(self, mock_run):
        manager = GEMINIManager()
        result = manager.start()
        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "up" in args

    @patch("gemini.manager.subprocess.run")
    def test_start_returns_false_on_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        manager = GEMINIManager()
        result = manager.start()
        assert result is False

    @patch("gemini.manager.subprocess.run")
    def test_stop_calls_subprocess(self, mock_run):
        manager = GEMINIManager()
        result = manager.stop()
        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "stop" in args

    @patch("gemini.manager.subprocess.run")
    def test_stop_returns_false_on_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        manager = GEMINIManager()
        result = manager.stop()
        assert result is False

    @patch("gemini.manager.subprocess.run")
    def test_clean_calls_subprocess(self, mock_run):
        manager = GEMINIManager()
        result = manager.clean()
        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "down" in args

    @patch("gemini.manager.subprocess.run")
    def test_clean_returns_false_on_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        manager = GEMINIManager()
        result = manager.clean()
        assert result is False

    @patch("gemini.manager.subprocess.run")
    def test_rebuild_calls_subprocess_three_times(self, mock_run):
        manager = GEMINIManager()
        result = manager.rebuild()
        assert result is True
        assert mock_run.call_count == 3

    @patch("gemini.manager.subprocess.run")
    def test_rebuild_returns_false_on_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        manager = GEMINIManager()
        result = manager.rebuild()
        assert result is False

    @patch("gemini.manager.subprocess.run")
    def test_update_calls_subprocess(self, mock_run):
        manager = GEMINIManager()
        result = manager.update()
        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "bash" in args

    @patch("gemini.manager.subprocess.run")
    def test_update_returns_false_on_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "bash")
        manager = GEMINIManager()
        result = manager.update()
        assert result is False


class TestSaveAndDeleteSettings:
    """Tests for save_settings() and delete_settings()."""

    def test_save_settings_creates_env_file(self):
        manager = GEMINIManager()
        with tempfile.NamedTemporaryFile(suffix=".env", delete=False) as f:
            path = f.name
        try:
            manager.env_file_path = path
            # delete_settings will try to remove the file
            manager.save_settings()
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert "GEMINI_DB_PORT=" in content
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_delete_settings_removes_file(self):
        manager = GEMINIManager()
        with tempfile.NamedTemporaryFile(suffix=".env", delete=False) as f:
            path = f.name
            f.write(b"TEST=value\n")
        manager.env_file_path = path
        manager.delete_settings()
        assert not os.path.exists(path)

    def test_delete_settings_handles_missing_file(self, capsys):
        manager = GEMINIManager()
        manager.env_file_path = "/nonexistent/path/.env"
        manager.delete_settings()
        captured = capsys.readouterr()
        assert "does not exist" in captured.out

    def test_delete_settings_handles_os_error(self, capsys):
        manager = GEMINIManager()
        manager.env_file_path = "/tmp/test_delete.env"
        with patch("gemini.manager.os.path.exists", return_value=True):
            with patch("gemini.manager.os.remove", side_effect=OSError("Permission denied")):
                manager.delete_settings()
                captured = capsys.readouterr()
                assert "Error deleting" in captured.out
