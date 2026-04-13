"""Tests for the Plot API class Pydantic model and validation."""

import pytest
from uuid import uuid4
from gemini.api.plot import Plot


class TestPlotModel:

    def test_construct_with_required_fields(self):
        plot = Plot(plot_number=1, plot_row_number=2, plot_column_number=3)
        assert plot.plot_number == 1
        assert plot.plot_row_number == 2
        assert plot.plot_column_number == 3
        assert plot.id is None
        assert plot.experiment_id is None
        assert plot.accession_id is None
        assert plot.population_id is None

    def test_construct_with_all_fields(self):
        uid = uuid4()
        eid = uuid4()
        sid = uuid4()
        sitid = uuid4()
        aid = uuid4()
        pid = uuid4()
        plot = Plot(
            id=uid,
            plot_number=10,
            plot_row_number=2,
            plot_column_number=5,
            experiment_id=eid,
            season_id=sid,
            site_id=sitid,
            accession_id=aid,
            population_id=pid,
            plot_info={"block": 1},
            plot_geometry_info={"wkt": "POLYGON(...)"},
        )
        assert plot.id == uid
        assert plot.accession_id == aid
        assert plot.population_id == pid
        assert plot.plot_info == {"block": 1}

    def test_id_alias_plot_id(self):
        uid = uuid4()
        plot = Plot.model_validate({
            "plot_id": str(uid),
            "plot_number": 1,
            "plot_row_number": 1,
            "plot_column_number": 1,
        })
        assert str(plot.id) == str(uid)

    def test_plot_number_is_required(self):
        with pytest.raises(Exception):
            Plot.model_validate({})

    def test_has_accession_and_population_fields(self):
        plot = Plot(plot_number=1, plot_row_number=1, plot_column_number=1)
        assert hasattr(plot, "accession_id")
        assert hasattr(plot, "population_id")

    def test_str_representation(self):
        plot = Plot(plot_number=42, plot_row_number=3, plot_column_number=7)
        s = str(plot)
        assert "42" in s
