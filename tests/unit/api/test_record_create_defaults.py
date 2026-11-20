"""Record creation defaults that used to drop or misfile records.

- ``timestamp`` must default to the time of the call, not the time the
  module was imported (records created later in a long-running process
  collided on the unique constraint and were silently skipped).
- Sensor records don't need plot coordinates; the coordinates only have to
  be complete when a plot is given, and 0 is a valid coordinate.
- ``insert_records`` without a dataset name files records under a dataset
  named after the collection date, not "... Dataset None".
"""
from datetime import date, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from gemini.api.dataset_record import DatasetRecord
from gemini.api.model_record import ModelRecord
from gemini.api.procedure_record import ProcedureRecord
from gemini.api.script_record import ScriptRecord
from gemini.api.sensor import Sensor
from gemini.api.sensor_record import SensorRecord
from gemini.api.trait import Trait
from gemini.api.trait_record import TraitRecord

COMMON = {"dataset_name": "DS", "experiment_name": "Exp", "insert_on_create": False}
PLOT = {"plot_number": 1, "plot_row_number": 1, "plot_column_number": 1}

CREATE_CASES = [
    (SensorRecord, {"sensor_name": "Cam", "sensor_data": {"v": 1}, **PLOT}),
    (TraitRecord, {"trait_name": "Height", "trait_value": 1.0}),
    (DatasetRecord, {"dataset_data": {"v": 1}}),
    (ModelRecord, {"model_name": "M", "model_data": {"v": 1}}),
    (ProcedureRecord, {"procedure_name": "P", "procedure_data": {"v": 1}}),
    (ScriptRecord, {"script_name": "S", "script_data": {"v": 1}}),
]


@pytest.mark.parametrize("cls,kwargs", CREATE_CASES, ids=[c[0].__name__ for c in CREATE_CASES])
def test_timestamp_defaults_to_time_of_call(cls, kwargs):
    before = datetime.now()
    record = cls.create(**COMMON, **kwargs)
    assert record is not None
    assert record.timestamp >= before


class TestSensorRecordPlotCoordinates:
    BASE = {**COMMON, "sensor_name": "Weather", "sensor_data": {"t": 21.5}}

    def test_create_without_plot(self):
        record = SensorRecord.create(**self.BASE)
        assert record is not None
        assert record.plot_number is None

    def test_create_with_zero_coordinates(self):
        record = SensorRecord.create(
            **self.BASE, plot_number=0, plot_row_number=0, plot_column_number=0
        )
        assert record is not None
        assert (record.plot_number, record.plot_row_number, record.plot_column_number) == (0, 0, 0)

    def test_create_rejects_partial_plot(self):
        assert SensorRecord.create(**self.BASE, plot_number=3) is None

    @pytest.mark.parametrize(
        "cls,view,name_kwarg",
        [
            (SensorRecord, "gemini.api.sensor_record.SensorRecordsIMMVModel", {"sensor_name": "Weather"}),
            (TraitRecord, "gemini.api.trait_record.TraitRecordsIMMVModel", {"trait_name": "Height"}),
        ],
        ids=["SensorRecord", "TraitRecord"],
    )
    def test_get_without_plot_queries_the_view(self, cls, view, name_kwarg):
        with patch(view) as view_model:
            view_model.get_by_parameters.return_value = None
            cls.get(
                timestamp=datetime(2024, 6, 15, 10, 0),
                dataset_name="DS",
                experiment_name="Exp",
                site_name="Davis",
                season_name="2024",
                **name_kwarg,
            )
        view_model.get_by_parameters.assert_called_once()


class TestInsertRecordsDefaultDatasetName:
    TIMESTAMPS = [datetime(2024, 6, 15, 10, 0), datetime(2024, 6, 15, 10, 1)]
    SCOPE = {"experiment_name": "Exp", "season_name": "2024", "site_name": "Davis"}

    def test_sensor(self):
        sensor = Sensor(
            id=uuid4(), sensor_name="Cam",
            sensor_type_id=0, sensor_data_type_id=0, sensor_data_format_id=0,
        )
        with patch("gemini.api.sensor.SensorRecord") as record_cls:
            record_cls.insert.return_value = (True, ["id"])
            sensor.insert_records(
                timestamps=self.TIMESTAMPS, sensor_data=[{"v": 1}, {"v": 2}], **self.SCOPE
            )
        names = {c.kwargs["dataset_name"] for c in record_cls.create.call_args_list}
        assert names == {"Cam Dataset 2024-06-15"}

    def test_trait(self):
        trait = Trait(id=uuid4(), trait_name="Height", trait_units="cm")
        with patch("gemini.api.trait.TraitRecord") as record_cls:
            record_cls.insert.return_value = (True, ["id"])
            trait.insert_records(
                timestamps=self.TIMESTAMPS, trait_values=[1.0, 2.0], **self.SCOPE
            )
        names = {c.kwargs["dataset_name"] for c in record_cls.create.call_args_list}
        assert names == {"Height Dataset 2024-06-15"}
