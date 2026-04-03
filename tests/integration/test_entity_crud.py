"""
Integration tests for ALL entity CRUD operations against real PostgreSQL.
No mocks. Every assertion hits the database.

Requires: docker compose -f tests/docker-compose.test.yaml up -d
"""
import pytest
import uuid
from datetime import date, datetime

pytestmark = pytest.mark.integration


# ============================================================
# Helper to build prerequisite entities
# ============================================================

class Fixtures:
    """Create real DB entities for tests that need foreign keys."""

    @staticmethod
    def experiment(name="Test Exp"):
        from gemini.db.models.experiments import ExperimentModel
        return ExperimentModel.get_or_create(experiment_name=name)

    @staticmethod
    def site(name="Test Site"):
        from gemini.db.models.sites import SiteModel
        return SiteModel.get_or_create(
            site_name=name, site_city="Davis", site_state="CA", site_country="USA"
        )

    @staticmethod
    def season(exp_id, name="2024"):
        from gemini.db.models.seasons import SeasonModel
        return SeasonModel.get_or_create(experiment_id=exp_id, season_name=name)

    @staticmethod
    def plot(exp_id, season_id, site_id, num=1, row=1, col=1):
        from gemini.db.models.plots import PlotModel
        return PlotModel.get_or_create(
            experiment_id=exp_id, season_id=season_id, site_id=site_id,
            plot_number=num, plot_row_number=row, plot_column_number=col
        )

    @staticmethod
    def cultivar(acc="ACC001", pop="POP_A"):
        from gemini.db.models.cultivars import CultivarModel
        return CultivarModel.get_or_create(cultivar_accession=acc, cultivar_population=pop)

    @staticmethod
    def sensor(name="Test Sensor"):
        from gemini.db.models.sensors import SensorModel
        return SensorModel.get_or_create(sensor_name=name)

    @staticmethod
    def dataset(name="Test Dataset"):
        from gemini.db.models.datasets import DatasetModel
        return DatasetModel.get_or_create(dataset_name=name)


# ============================================================
# Cultivar
# ============================================================

class TestCultivarCRUD:

    def test_create(self, setup_real_db):
        from gemini.db.models.cultivars import CultivarModel
        c = CultivarModel.create(cultivar_accession="A001", cultivar_population="Pop1")
        assert c.cultivar_accession == "A001"
        assert c.cultivar_population == "Pop1"
        assert c.id is not None

    def test_unique_constraint(self, setup_real_db):
        from gemini.db.models.cultivars import CultivarModel
        CultivarModel.create(cultivar_accession="U1", cultivar_population="P1")
        dup = CultivarModel.get_or_create(cultivar_accession="U1", cultivar_population="P1")
        assert CultivarModel.search(cultivar_accession="U1", cultivar_population="P1")
        assert len(CultivarModel.search(cultivar_accession="U1")) == 1

    def test_update_info(self, setup_real_db):
        from gemini.db.models.cultivars import CultivarModel
        c = CultivarModel.create(cultivar_accession="UPD", cultivar_population="P")
        CultivarModel.update(c, cultivar_info={"color": "green"})
        fetched = CultivarModel.get(c.id)
        assert fetched.cultivar_info["color"] == "green"

    def test_delete(self, setup_real_db):
        from gemini.db.models.cultivars import CultivarModel
        c = CultivarModel.create(cultivar_accession="DEL", cultivar_population="P")
        CultivarModel.delete(c)
        assert CultivarModel.get(c.id) is None


# ============================================================
# Sensor + SensorType + SensorPlatform
# ============================================================

class TestSensorCRUD:

    def test_create_sensor_with_defaults(self, setup_real_db):
        from gemini.db.models.sensors import SensorModel
        s = SensorModel.create(sensor_name="RGB Camera")
        assert s.sensor_name == "RGB Camera"
        assert s.id is not None

    def test_create_sensor_with_type_ref(self, setup_real_db):
        from gemini.db.models.sensors import SensorModel
        # sensor_type_id=1 is "RGB" from seed data
        s = SensorModel.create(sensor_name="Typed Sensor", sensor_type_id=1)
        fetched = SensorModel.get(s.id)
        assert fetched.sensor_type_id == 1

    def test_search_by_name(self, setup_real_db):
        from gemini.db.models.sensors import SensorModel
        SensorModel.create(sensor_name="Searchable Sensor")
        results = SensorModel.search(sensor_name="Searchable Sensor")
        assert len(results) == 1

    def test_update_sensor_info(self, setup_real_db):
        from gemini.db.models.sensors import SensorModel
        s = SensorModel.create(sensor_name="Info Sensor")
        SensorModel.update(s, sensor_info={"resolution": "4K"})
        fetched = SensorModel.get(s.id)
        assert fetched.sensor_info["resolution"] == "4K"


class TestSensorTypeCRUD:

    def test_seed_data_exists(self, setup_real_db):
        from gemini.db.models.sensor_types import SensorTypeModel
        types = SensorTypeModel.all()
        assert len(types) >= 4  # Default, RGB, NIR, Thermal from seed
        names = [t.sensor_type_name for t in types]
        assert "RGB" in names

    def test_create_custom_type(self, setup_real_db):
        from gemini.db.models.sensor_types import SensorTypeModel
        st = SensorTypeModel.get_or_create(sensor_type_name="LiDAR")
        assert st.sensor_type_name == "LiDAR"


class TestSensorPlatformCRUD:

    def test_create_and_get(self, setup_real_db):
        from gemini.db.models.sensor_platforms import SensorPlatformModel
        sp = SensorPlatformModel.create(
            sensor_platform_name="Drone A",
            sensor_platform_info={"type": "UAV"}
        )
        fetched = SensorPlatformModel.get(sp.id)
        assert fetched.sensor_platform_name == "Drone A"
        assert fetched.sensor_platform_info["type"] == "UAV"


# ============================================================
# Trait + TraitLevel
# ============================================================

class TestTraitCRUD:

    def test_create_with_units(self, setup_real_db):
        from gemini.db.models.traits import TraitModel
        t = TraitModel.create(trait_name="Plant Height", trait_units="cm")
        assert t.trait_name == "Plant Height"
        assert t.trait_units == "cm"

    def test_create_with_metrics(self, setup_real_db):
        from gemini.db.models.traits import TraitModel
        t = TraitModel.create(
            trait_name="NDVI",
            trait_metrics={"min": 0.0, "max": 1.0}
        )
        fetched = TraitModel.get(t.id)
        assert fetched.trait_metrics["max"] == 1.0

    def test_search_by_name(self, setup_real_db):
        from gemini.db.models.traits import TraitModel
        TraitModel.create(trait_name="Leaf Area")
        results = TraitModel.search(trait_name="Leaf Area")
        assert len(results) == 1


class TestTraitLevelCRUD:

    def test_seed_data(self, setup_real_db):
        from gemini.db.models.trait_levels import TraitLevelModel
        levels = TraitLevelModel.all()
        names = [l.trait_level_name for l in levels]
        assert "Plot" in names
        assert "Plant" in names


# ============================================================
# Dataset + DatasetType
# ============================================================

class TestDatasetCRUD:

    def test_create(self, setup_real_db):
        from gemini.db.models.datasets import DatasetModel
        d = DatasetModel.create(dataset_name="Field Scan 2024")
        assert d.dataset_name == "Field Scan 2024"
        assert d.id is not None

    def test_with_type_ref(self, setup_real_db):
        from gemini.db.models.datasets import DatasetModel
        # dataset_type_id=1 is "Sensor" from seed data
        d = DatasetModel.create(dataset_name="Sensor Dataset", dataset_type_id=1)
        fetched = DatasetModel.get(d.id)
        assert fetched.dataset_type_id == 1

    def test_update_info(self, setup_real_db):
        from gemini.db.models.datasets import DatasetModel
        d = DatasetModel.create(dataset_name="Update DS")
        DatasetModel.update(d, dataset_info={"source": "drone"})
        fetched = DatasetModel.get(d.id)
        assert fetched.dataset_info["source"] == "drone"


class TestDatasetTypeCRUD:

    def test_seed_data(self, setup_real_db):
        from gemini.db.models.dataset_types import DatasetTypeModel
        types = DatasetTypeModel.all()
        names = [t.dataset_type_name for t in types]
        assert "Sensor" in names
        assert "Trait" in names


# ============================================================
# DataType + DataFormat
# ============================================================

class TestDataTypeCRUD:

    def test_seed_data(self, setup_real_db):
        from gemini.db.models.data_types import DataTypeModel
        types = DataTypeModel.all()
        names = [t.data_type_name for t in types]
        assert "Image" in names
        assert "Text" in names

    def test_create_custom(self, setup_real_db):
        from gemini.db.models.data_types import DataTypeModel
        dt = DataTypeModel.get_or_create(data_type_name="Genomics")
        assert dt.data_type_name == "Genomics"


class TestDataFormatCRUD:

    def test_seed_data(self, setup_real_db):
        from gemini.db.models.data_formats import DataFormatModel
        formats = DataFormatModel.all()
        names = [f.data_format_name for f in formats]
        assert "CSV" in names
        assert "JPEG" in names

    def test_mime_type(self, setup_real_db):
        from gemini.db.models.data_formats import DataFormatModel
        f = DataFormatModel.get_by_parameters(data_format_name="CSV")
        assert f.data_format_mime_type == "text/csv"


# ============================================================
# Model + ModelRun
# ============================================================

class TestModelCRUD:

    def test_create(self, setup_real_db):
        from gemini.db.models.models import ModelModel
        m = ModelModel.create(model_name="YOLOv8", model_url="https://example.com/yolo")
        assert m.model_name == "YOLOv8"

    def test_update_info(self, setup_real_db):
        from gemini.db.models.models import ModelModel
        m = ModelModel.create(model_name="ResNet", model_url="https://example.com/resnet")
        ModelModel.update(m, model_info={"accuracy": 0.95})
        fetched = ModelModel.get(m.id)
        assert fetched.model_info["accuracy"] == 0.95


class TestModelRunCRUD:

    def test_create_run(self, setup_real_db):
        from gemini.db.models.models import ModelModel
        from gemini.db.models.model_runs import ModelRunModel
        m = ModelModel.create(model_name="RunModel", model_url="http://x")
        run = ModelRunModel.create(
            model_id=m.id,
            model_run_info={"epoch": 10, "loss": 0.05}
        )
        assert run.model_id is not None

    def test_cascade_delete(self, setup_real_db):
        from gemini.db.models.models import ModelModel
        from gemini.db.models.model_runs import ModelRunModel
        m = ModelModel.create(model_name="CascModel", model_url="http://y")
        run = ModelRunModel.create(model_id=m.id, model_run_info={"run": 1})
        run_id = run.id
        ModelModel.delete(m)
        assert ModelRunModel.get(run_id) is None


# ============================================================
# Script + ScriptRun
# ============================================================

class TestScriptCRUD:

    def test_create(self, setup_real_db):
        from gemini.db.models.scripts import ScriptModel
        s = ScriptModel.create(
            script_name="preprocess.py",
            script_url="https://github.com/example/scripts",
            script_extension=".py"
        )
        assert s.script_name == "preprocess.py"


class TestScriptRunCRUD:

    def test_create_and_cascade(self, setup_real_db):
        from gemini.db.models.scripts import ScriptModel
        from gemini.db.models.script_runs import ScriptRunModel
        s = ScriptModel.create(script_name="run_test.sh", script_url="http://z")
        run = ScriptRunModel.create(script_id=s.id, script_run_info={"status": "ok"})
        assert run.id is not None
        ScriptModel.delete(s)
        assert ScriptRunModel.get(run.id) is None


# ============================================================
# Procedure + ProcedureRun
# ============================================================

class TestProcedureCRUD:

    def test_create(self, setup_real_db):
        from gemini.db.models.procedures import ProcedureModel
        p = ProcedureModel.create(procedure_name="Irrigation Protocol")
        assert p.procedure_name == "Irrigation Protocol"


class TestProcedureRunCRUD:

    def test_create_and_cascade(self, setup_real_db):
        from gemini.db.models.procedures import ProcedureModel
        from gemini.db.models.procedure_runs import ProcedureRunModel
        p = ProcedureModel.create(procedure_name="Cascade Proc")
        run = ProcedureRunModel.create(procedure_id=p.id, procedure_run_info={"step": 1})
        assert run.id is not None
        ProcedureModel.delete(p)
        assert ProcedureRunModel.get(run.id) is None


# ============================================================
# Plant (requires plot → requires experiment + season + site)
# ============================================================

class TestPlantCRUD:

    def test_create_plant_in_plot(self, setup_real_db):
        from gemini.db.models.plants import PlantModel
        exp = Fixtures.experiment("Plant Exp")
        season = Fixtures.season(exp.id)
        site = Fixtures.site("Plant Site")
        plot = Fixtures.plot(exp.id, season.id, site.id)
        cultivar = Fixtures.cultivar("PACC", "PPOP")

        plant = PlantModel.create(
            plot_id=plot.id, plant_number=1, cultivar_id=cultivar.id
        )
        assert plant.plot_id is not None
        assert plant.plant_number == 1

    def test_unique_plant_number_per_plot(self, setup_real_db):
        from gemini.db.models.plants import PlantModel
        exp = Fixtures.experiment("PlantU Exp")
        season = Fixtures.season(exp.id, "UniSeason")
        site = Fixtures.site("PlantU Site")
        plot = Fixtures.plot(exp.id, season.id, site.id)
        cultivar = Fixtures.cultivar("UACC", "UPOP")

        PlantModel.create(plot_id=plot.id, plant_number=1, cultivar_id=cultivar.id)
        dup = PlantModel.get_or_create(plot_id=plot.id, plant_number=1, cultivar_id=cultivar.id)
        assert dup is not None
        assert PlantModel.count() == 1


# ============================================================
# Season (additional tests beyond what test_db_crud.py covers)
# ============================================================

class TestSeasonCRUD:

    def test_create_with_dates(self, setup_real_db):
        from gemini.db.models.seasons import SeasonModel
        exp = Fixtures.experiment("Season Date Exp")
        s = SeasonModel.create(
            experiment_id=exp.id, season_name="Spring 2024",
            season_start_date=date(2024, 3, 1),
            season_end_date=date(2024, 6, 30)
        )
        fetched = SeasonModel.get(s.id)
        assert fetched.season_start_date == date(2024, 3, 1)
        assert fetched.season_end_date == date(2024, 6, 30)

    def test_unique_per_experiment(self, setup_real_db):
        from gemini.db.models.seasons import SeasonModel
        exp = Fixtures.experiment("Season Uniq Exp")
        SeasonModel.create(experiment_id=exp.id, season_name="2024")
        dup = SeasonModel.get_or_create(experiment_id=exp.id, season_name="2024")
        assert dup is not None
        assert len(SeasonModel.search(season_name="2024")) == 1


# ============================================================
# Resource
# ============================================================

class TestResourceCRUD:

    def test_create(self, setup_real_db):
        from gemini.db.models.resources import ResourceModel
        r = ResourceModel.create(
            resource_uri="/data/images/", resource_file_name="scan_001.tiff"
        )
        assert r.resource_file_name == "scan_001.tiff"
        assert r.is_external is False
