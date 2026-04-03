"""Tests for gemini.cli.__main__ CLI commands."""
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from gemini.cli.__main__ import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_manager():
    """Patch GEMINIManager at the point it's used in the CLI module."""
    with patch("gemini.cli.__main__.GEMINIManager") as MockClass:
        instance = MagicMock()
        instance.build.return_value = True
        instance.start.return_value = True
        instance.stop.return_value = True
        instance.clean.return_value = True
        instance.rebuild.return_value = True
        instance.update.return_value = True
        instance.save_settings.return_value = None
        MockClass.return_value = instance
        yield instance


class TestBuildCommand:
    def test_build_success(self, runner, mock_manager):
        result = runner.invoke(cli, ["build"])
        assert result.exit_code == 0
        mock_manager.build.assert_called_once()

    def test_build_output(self, runner, mock_manager):
        result = runner.invoke(cli, ["build"])
        assert "Building GEMINI pipeline" in result.output
        assert "GEMINI pipeline built" in result.output


class TestStartCommand:
    def test_start_success(self, runner, mock_manager):
        result = runner.invoke(cli, ["start"])
        assert result.exit_code == 0
        mock_manager.start.assert_called_once()

    def test_start_output(self, runner, mock_manager):
        result = runner.invoke(cli, ["start"])
        assert "Starting GEMINI pipeline" in result.output


class TestStopCommand:
    def test_stop_success(self, runner, mock_manager):
        result = runner.invoke(cli, ["stop"])
        assert result.exit_code == 0
        mock_manager.stop.assert_called_once()

    def test_stop_output(self, runner, mock_manager):
        result = runner.invoke(cli, ["stop"])
        assert "Stopping GEMINI pipeline" in result.output


class TestCleanCommand:
    def test_clean_success(self, runner, mock_manager):
        result = runner.invoke(cli, ["clean"])
        assert result.exit_code == 0
        mock_manager.clean.assert_called_once()

    def test_clean_output(self, runner, mock_manager):
        result = runner.invoke(cli, ["clean"])
        assert "Cleaning GEMINI pipeline" in result.output


class TestResetCommand:
    def test_reset_success(self, runner, mock_manager):
        result = runner.invoke(cli, ["reset"])
        assert result.exit_code == 0
        mock_manager.save_settings.assert_called_once()
        mock_manager.rebuild.assert_called_once()

    def test_reset_output(self, runner, mock_manager):
        result = runner.invoke(cli, ["reset"])
        assert "Resetting GEMINI pipeline" in result.output
        assert "GEMINI pipeline reset" in result.output


class TestSetupCommand:
    def test_setup_success(self, runner, mock_manager):
        result = runner.invoke(cli, ["setup"])
        assert result.exit_code == 0
        mock_manager.save_settings.assert_called_once()
        mock_manager.rebuild.assert_called_once()

    def test_setup_with_default_flag(self, runner, mock_manager):
        result = runner.invoke(cli, ["setup", "--default"])
        assert result.exit_code == 0
        mock_manager.save_settings.assert_called_once()
        mock_manager.rebuild.assert_called_once()

    def test_setup_output(self, runner, mock_manager):
        result = runner.invoke(cli, ["setup"])
        assert "Setting up GEMINI pipeline" in result.output
        assert "GEMINI pipeline setup complete" in result.output


class TestUpdateCommand:
    def test_update_success(self, runner, mock_manager):
        result = runner.invoke(cli, ["update"])
        assert result.exit_code == 0
        mock_manager.update.assert_called_once()
        mock_manager.save_settings.assert_called_once()
        mock_manager.rebuild.assert_called_once()

    def test_update_output(self, runner, mock_manager):
        result = runner.invoke(cli, ["update"])
        assert "Updating GEMINI pipeline" in result.output
        assert "GEMINI pipeline updated" in result.output


class TestCLIHelp:
    def test_cli_help(self, runner, mock_manager):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "GEMINI CLI" in result.output

    def test_build_help(self, runner, mock_manager):
        result = runner.invoke(cli, ["build", "--help"])
        assert result.exit_code == 0
        assert "Builds the GEMINI pipeline" in result.output
