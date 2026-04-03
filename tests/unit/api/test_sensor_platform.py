"""Tests for gemini.api.sensor_platform module - SensorPlatform class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.sensor_platform import SensorPlatform

MODULE = "gemini.api.sensor_platform"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "sensor_platform_name": "Drone1", "sensor_platform_info": {"k": "v"}}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestSensorPlatformExists:
    @patch(f"{MODULE}.SensorPlatformModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert SensorPlatform.exists(sensor_platform_name="Drone1") is True

    @patch(f"{MODULE}.SensorPlatformModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert SensorPlatform.exists(sensor_platform_name="X") is False

    @patch(f"{MODULE}.SensorPlatformModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert SensorPlatform.exists(sensor_platform_name="X") is False


class TestSensorPlatformCreate:
    @patch(f"{MODULE}.SensorPlatformModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        assert SensorPlatform.create(sensor_platform_name="Drone1") is not None

    @patch(f"{MODULE}.SensorPlatformModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert SensorPlatform.create(sensor_platform_name="X") is None


class TestSensorPlatformGet:
    @patch(f"{MODULE}.ExperimentSensorPlatformsViewModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert SensorPlatform.get(sensor_platform_name="Drone1") is not None

    @patch(f"{MODULE}.ExperimentSensorPlatformsViewModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert SensorPlatform.get(sensor_platform_name="X") is None


class TestSensorPlatformGetById:
    @patch(f"{MODULE}.SensorPlatformModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert SensorPlatform.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.SensorPlatformModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert SensorPlatform.get_by_id(uuid4()) is None


class TestSensorPlatformGetAll:
    @patch(f"{MODULE}.SensorPlatformModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(SensorPlatform.get_all()) == 1

    @patch(f"{MODULE}.SensorPlatformModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert SensorPlatform.get_all() is None


class TestSensorPlatformSearch:
    @patch(f"{MODULE}.ExperimentSensorPlatformsViewModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(SensorPlatform.search(sensor_platform_name="Drone1")) == 1

    def test_no_params(self):
        assert SensorPlatform.search() is None

    @patch(f"{MODULE}.ExperimentSensorPlatformsViewModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert SensorPlatform.search(sensor_platform_name="X") is None


class TestSensorPlatformUpdate:
    @patch(f"{MODULE}.SensorPlatformModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, sensor_platform_name="New")
        sp = SensorPlatform(id=uid, sensor_platform_name="Old")
        assert sp.update(sensor_platform_name="New") is not None

    @patch(f"{MODULE}.SensorPlatformModel")
    def test_no_params(self, m):
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        assert sp.update() is None

    @patch(f"{MODULE}.SensorPlatformModel")
    def test_not_found(self, m):
        m.get.return_value = None
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        assert sp.update(sensor_platform_name="New") is None


class TestSensorPlatformDelete:
    @patch(f"{MODULE}.SensorPlatformModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        assert sp.delete() is True

    @patch(f"{MODULE}.SensorPlatformModel")
    def test_not_found(self, m):
        m.get.return_value = None
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        assert sp.delete() is False


class TestSensorPlatformRefresh:
    @patch(f"{MODULE}.SensorPlatformModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        sp = SensorPlatform(id=uid, sensor_platform_name="X")
        assert sp.refresh() is sp

    @patch(f"{MODULE}.SensorPlatformModel")
    def test_not_found(self, m):
        m.get.return_value = None
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        assert sp.refresh() is sp


class TestSensorPlatformGetSetInfo:
    @patch(f"{MODULE}.SensorPlatformModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(sensor_platform_info={"k": "v"})
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        assert sp.get_info() == {"k": "v"}

    @patch(f"{MODULE}.SensorPlatformModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(sensor_platform_info=None)
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        assert sp.get_info() is None

    @patch(f"{MODULE}.SensorPlatformModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        sp = SensorPlatform(id=uid, sensor_platform_name="X")
        assert sp.set_info({"new": "v"}) is not None


class TestSensorPlatformAssociations:
    @patch(f"{MODULE}.SensorPlatformSensorsViewModel")
    def test_get_associated_sensors(self, m):
        m.search.return_value = [MagicMock()]
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        result = sp.get_associated_sensors()
        m.search.assert_called_once()

    @patch(f"{MODULE}.SensorPlatformSensorsViewModel")
    def test_get_associated_sensors_empty(self, m):
        m.search.return_value = []
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        assert sp.get_associated_sensors() is None

    @patch(f"{MODULE}.ExperimentSensorPlatformsViewModel")
    def test_get_associated_experiments(self, m):
        m.search.return_value = [MagicMock()]
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.experiment.Experiment", create=True):
            result = sp.get_associated_experiments()
            m.search.assert_called_once()

    @patch(f"{MODULE}.ExperimentSensorPlatformsViewModel")
    def test_get_associated_experiments_empty(self, m):
        m.search.return_value = []
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        assert sp.get_associated_experiments() is None

    def test_create_new_sensor_success(self):
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.create.return_value = MagicMock()
            result = sp.create_new_sensor("Sensor1")
            assert result is not None

    def test_create_new_sensor_failure(self):
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.create.return_value = None
            assert sp.create_new_sensor("Sensor1") is None

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_associate_sensor_success(self, m_assoc):
        m_assoc.exists.return_value = False
        m_assoc.get_or_create.return_value = MagicMock()
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.get.return_value = MagicMock(id=uuid4())
            with patch.object(SensorPlatform, "refresh"):
                result = sp.associate_sensor("Sensor1")
                assert result is not None

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_associate_sensor_not_found(self, m_assoc):
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.get.return_value = None
            assert sp.associate_sensor("Missing") is None

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_unassociate_sensor_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.get.return_value = MagicMock(id=uuid4())
            with patch.object(sp, "refresh"):
                result = sp.unassociate_sensor("Sensor1")
                assert result is not None

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_unassociate_sensor_not_associated(self, m_assoc):
        m_assoc.get_by_parameters.return_value = None
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.get.return_value = MagicMock(id=uuid4())
            assert sp.unassociate_sensor("Sensor1") is None

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_belongs_to_sensor_true(self, m_assoc):
        m_assoc.exists.return_value = True
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.get.return_value = MagicMock(id=uuid4())
            assert sp.belongs_to_sensor("Sensor1") is True

    @patch(f"{MODULE}.SensorPlatformSensorModel")
    def test_belongs_to_sensor_not_found(self, m_assoc):
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.sensor.Sensor") as mock_sen:
            mock_sen.get.return_value = None
            assert sp.belongs_to_sensor("Missing") is False

    @patch(f"{MODULE}.ExperimentSensorPlatformModel")
    def test_associate_experiment_success(self, m_assoc):
        m_assoc.exists.return_value = False
        m_assoc.get_or_create.return_value = MagicMock()
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.experiment.Experiment") as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(SensorPlatform, "refresh"):
                result = sp.associate_experiment("Exp1")
                assert result is not None

    def test_associate_experiment_not_found(self):
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = None
            assert sp.associate_experiment("Missing") is None

    @patch(f"{MODULE}.ExperimentSensorPlatformModel")
    def test_unassociate_experiment_success(self, m_assoc):
        m_assoc.get_by_parameters.return_value = MagicMock()
        m_assoc.delete.return_value = True
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            with patch.object(sp, "refresh"):
                result = sp.unassociate_experiment("Exp1")
                assert result is not None

    @patch(f"{MODULE}.ExperimentSensorPlatformModel")
    def test_belongs_to_experiment_true(self, m_assoc):
        m_assoc.exists.return_value = True
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert sp.belongs_to_experiment("Exp1") is True

    @patch(f"{MODULE}.ExperimentSensorPlatformModel")
    def test_belongs_to_experiment_false(self, m_assoc):
        m_assoc.exists.return_value = False
        sp = SensorPlatform(id=uuid4(), sensor_platform_name="X")
        with patch("gemini.api.experiment.Experiment", create=True) as mock_exp:
            mock_exp.get.return_value = MagicMock(id=uuid4())
            assert sp.belongs_to_experiment("Exp1") is False
