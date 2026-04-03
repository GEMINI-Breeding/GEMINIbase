"""Tests for gemini.api.sensor module - Sensor class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.sensor import Sensor

MODULE = "gemini.api.sensor"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(), "sensor_name": "TempSensor",
        "sensor_type_id": 1, "sensor_data_type_id": 0,
        "sensor_data_format_id": 0, "sensor_info": {"k": "v"},
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestSensorExists:
    @patch(f"{MODULE}.SensorModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert Sensor.exists(sensor_name="TempSensor") is True

    @patch(f"{MODULE}.SensorModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert Sensor.exists(sensor_name="X") is False

    @patch(f"{MODULE}.SensorModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert Sensor.exists(sensor_name="X") is False


class TestSensorCreate:
    @patch(f"{MODULE}.SensorModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        result = Sensor.create(sensor_name="TempSensor")
        assert result is not None

    @patch(f"{MODULE}.SensorModel")
    def test_with_experiment(self, m):
        m.get_or_create.return_value = _make_db()
        with patch.object(Sensor, "associate_experiment", return_value=MagicMock()):
            with patch.object(Sensor, "associate_sensor_platform", return_value=MagicMock()):
                result = Sensor.create(sensor_name="TempSensor", experiment_name="Exp1", sensor_platform_name="Platform1")
                assert result is not None

    @patch(f"{MODULE}.SensorModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert Sensor.create(sensor_name="X") is None


class TestSensorGet:
    @patch(f"{MODULE}.SensorModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert Sensor.get(sensor_name="TempSensor") is not None

    @patch(f"{MODULE}.SensorModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert Sensor.get(sensor_name="X") is None

    @patch(f"{MODULE}.SensorModel")
    def test_exception(self, m):
        m.get_by_parameters.side_effect = Exception("err")
        assert Sensor.get(sensor_name="X") is None


class TestSensorGetById:
    @patch(f"{MODULE}.SensorModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert Sensor.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.SensorModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert Sensor.get_by_id(uuid4()) is None


class TestSensorGetAll:
    @patch(f"{MODULE}.SensorModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(Sensor.get_all()) == 1

    @patch(f"{MODULE}.SensorModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert Sensor.get_all() is None


class TestSensorSearch:
    @patch(f"{MODULE}.ExperimentSensorsViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(Sensor.search(sensor_name="TempSensor")) == 1

    def test_no_params(self):
        assert Sensor.search() is None

    @patch(f"{MODULE}.ExperimentSensorsViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert Sensor.search(sensor_name="X") is None


class TestSensorUpdate:
    @patch(f"{MODULE}.SensorModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, sensor_name="New")
        s = Sensor(id=uid, sensor_name="Old", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.update(sensor_name="New") is not None

    @patch(f"{MODULE}.SensorModel")
    def test_no_params(self, m):
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.update() is None

    @patch(f"{MODULE}.SensorModel")
    def test_not_found(self, m):
        m.get.return_value = None
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.update(sensor_name="New") is None


class TestSensorDelete:
    @patch(f"{MODULE}.SensorModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.delete() is True

    @patch(f"{MODULE}.SensorModel")
    def test_not_found(self, m):
        m.get.return_value = None
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.delete() is False


class TestSensorRefresh:
    @patch(f"{MODULE}.SensorModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        s = Sensor(id=uid, sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.refresh() is s

    @patch(f"{MODULE}.SensorModel")
    def test_not_found(self, m):
        m.get.return_value = None
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.refresh() is s


class TestSensorGetSetInfo:
    @patch(f"{MODULE}.SensorModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(sensor_info={"k": "v"})
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.get_info() == {"k": "v"}

    @patch(f"{MODULE}.SensorModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(sensor_info=None)
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.get_info() is None

    @patch(f"{MODULE}.SensorModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        s = Sensor(id=uid, sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.set_info({"new": "v"}) is not None


class TestSensorAssociations:
    @patch(f"{MODULE}.SensorPlatformSensorsViewModel")
    def test_get_associated_sensor_platforms(self, m):
        m.search.return_value = [MagicMock()]
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.sensor_platform.SensorPlatform", create=True):
            result = s.get_associated_sensor_platforms()
            m.search.assert_called_once()

    @patch(f"{MODULE}.SensorPlatformSensorsViewModel")
    def test_get_associated_sensor_platforms_empty(self, m):
        m.search.return_value = []
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.get_associated_sensor_platforms() is None

    @patch(f"{MODULE}.ExperimentSensorsViewModel")
    def test_get_associated_experiments(self, m):
        m.search.return_value = [MagicMock()]
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.experiment.Experiment", create=True):
            result = s.get_associated_experiments()
            m.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentSensorsViewModel")
    def test_get_associated_experiments_empty(self, m):
        m.search.return_value = []
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.get_associated_experiments() is None

    @patch(f"{MODULE}.ExperimentSensorModel")
    def test_associate_experiment(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(s, "refresh"):
                result = s.associate_experiment("Exp1")

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_belongs_to_sensor_platform(self, m_assoc):
        m_assoc.exists.return_value = True
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_sp.get.return_value = MagicMock(id=uuid4())
            assert s.belongs_to_sensor_platform("Platform1") is True

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_belongs_to_sensor_platform_not_found(self, m_assoc):
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_sp.get.return_value = None
            assert s.belongs_to_sensor_platform("Missing") is False

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_associate_sensor_platform_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_sp.get.return_value = MagicMock(id=uuid4())
            with patch.object(s, "refresh"):
                result = s.associate_sensor_platform("Platform1")
                assert result is not None

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_associate_sensor_platform_not_found(self, m_assoc):
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_sp.get.return_value = None
            assert s.associate_sensor_platform("Missing") is None

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_associate_sensor_platform_already_associated(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_sp.get.return_value = MagicMock(id=uuid4())
            assert s.associate_sensor_platform("Platform1") is None

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_unassociate_sensor_platform_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_sp.get.return_value = MagicMock(id=uuid4())
            with patch.object(s, "refresh"):
                result = s.unassociate_sensor_platform("Platform1")
                assert result is not None

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_unassociate_sensor_platform_not_associated(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.sensor_platform.SensorPlatform") as mock_sp:
            mock_sp.get.return_value = MagicMock(id=uuid4())
            assert s.unassociate_sensor_platform("Platform1") is None

    @patch(f"{MODULE}.ExperimentSensorModel")
    def test_unassociate_experiment_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(s, "refresh"):
                result = s.unassociate_experiment("Exp1")
                assert result is not None

    @patch(f"{MODULE}.ExperimentSensorModel")
    def test_unassociate_experiment_not_associated(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert s.unassociate_experiment("Exp1") is None

    @patch(f"{MODULE}.ExperimentSensorModel")
    def test_belongs_to_experiment_true(self, m_assoc):
        m_assoc.exists.return_value = True
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert s.belongs_to_experiment("Exp1") is True

    @patch(f"{MODULE}.ExperimentSensorModel")
    def test_belongs_to_experiment_exp_not_found(self, m_assoc):
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = None
            assert s.belongs_to_experiment("Missing") is False

    @patch(f"{MODULE}.SensorDatasetsViewModel")
    def test_get_associated_datasets_found(self, m):
        m.search.return_value = [MagicMock()]
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        result = s.get_associated_datasets()
        m.search.assert_called_once()

    @patch(f"{MODULE}.SensorDatasetsViewModel")
    def test_get_associated_datasets_empty(self, m):
        m.search.return_value = []
        s = Sensor(id=uuid4(), sensor_name="X", sensor_type_id=1, sensor_data_type_id=0, sensor_data_format_id=0)
        assert s.get_associated_datasets() is None
