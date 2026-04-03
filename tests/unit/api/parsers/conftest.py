"""Fixtures for parser unit tests."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

FIXTURES_DIR = Path(__file__).parents[3] / "fixtures"


@pytest.fixture
def amiga_phone_dir():
    """Absolute path to the AMIGA Phone fixture directory."""
    return str(
        FIXTURES_DIR
        / "amiga"
        / "Dataset_2024"
        / "Davis"
        / "2024-07-15"
        / "Amiga_Phone"
        / "Phone"
    )


@pytest.fixture
def drone_dir():
    """Path to the drone fixture directory."""
    return FIXTURES_DIR / "drone"


@pytest.fixture
def mock_db_boundary():
    """
    Patches only the DB-layer calls that require a live PostgreSQL connection.
    All parser logic (file reading, JSON parsing, data-map construction) runs for real.
    Returns a dict of the mock sensor objects so tests can assert on add_records calls.
    """
    mock_experiment = MagicMock()
    mock_experiment.experiment_name = "GEMINI"
    mock_experiment.get_sites.return_value = [MagicMock(site_name="Davis")]
    mock_experiment.get_seasons.return_value = [MagicMock(season_name="2024")]

    mock_platform = MagicMock()
    mock_platform.get_sensors.return_value = []

    mock_sensors = {
        "AMIGA Phone Camera Metadata": MagicMock(),
        "AMIGA Phone Confidence": MagicMock(),
        "AMIGA Phone Depth Sensor": MagicMock(),
        "AMIGA Phone Thermal Camera": MagicMock(),
        "AMIGA Phone RGB Camera": MagicMock(),
    }

    def sensor_get(sensor_name, experiment_name):
        return mock_sensors[sensor_name]

    with (
        patch("gemini.api.parsers.amiga.Experiment.get", return_value=mock_experiment),
        patch("gemini.api.parsers.amiga.SensorPlatform.get", return_value=mock_platform),
        patch("gemini.api.parsers.amiga.Sensor.get", side_effect=sensor_get),
    ):
        yield mock_sensors
