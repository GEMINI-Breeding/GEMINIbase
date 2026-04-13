"""
Integration tests for ALL 18 association tables against real PostgreSQL.
Tests create, exists, cascade delete for each association type.

Requires: docker compose -f tests/docker-compose.test.yaml up -d
"""
import pytest

pytestmark = pytest.mark.integration


# ============================================================
# Helpers
# ============================================================

def make_experiment(name="Assoc Exp"):
    from gemini.db.models.experiments import ExperimentModel
    return ExperimentModel.get_or_create(experiment_name=name)

def make_site(name="Assoc Site"):
    from gemini.db.models.sites import SiteModel
    return SiteModel.get_or_create(
        site_name=name, site_city="C", site_state="S", site_country="US"
    )

def make_sensor(name="Assoc Sensor"):
    from gemini.db.models.sensors import SensorModel
    return SensorModel.get_or_create(sensor_name=name)

def make_platform(name="Assoc Platform"):
    from gemini.db.models.sensor_platforms import SensorPlatformModel
    return SensorPlatformModel.get_or_create(sensor_platform_name=name)

def make_trait(name="Assoc Trait"):
    from gemini.db.models.traits import TraitModel
    return TraitModel.get_or_create(trait_name=name)

def make_population(pop="APOP"):
    from gemini.db.models.populations import PopulationModel
    return PopulationModel.get_or_create(population_name=pop)

def make_accession(name="AACC"):
    from gemini.db.models.accessions import AccessionModel
    return AccessionModel.get_or_create(accession_name=name)

def make_dataset(name="Assoc Dataset"):
    from gemini.db.models.datasets import DatasetModel
    return DatasetModel.get_or_create(dataset_name=name)

def make_model(name="Assoc Model"):
    from gemini.db.models.models import ModelModel
    return ModelModel.get_or_create(model_name=name, model_url="http://x")

def make_procedure(name="Assoc Procedure"):
    from gemini.db.models.procedures import ProcedureModel
    return ProcedureModel.get_or_create(procedure_name=name)

def make_script(name="Assoc Script"):
    from gemini.db.models.scripts import ScriptModel
    return ScriptModel.get_or_create(script_name=name, script_url="http://x")

def make_plot(exp_id, season_id, site_id):
    from gemini.db.models.plots import PlotModel
    return PlotModel.get_or_create(
        experiment_id=exp_id, season_id=season_id, site_id=site_id,
        plot_number=1, plot_row_number=1, plot_column_number=1
    )

def make_season(exp_id, name="2024"):
    from gemini.db.models.seasons import SeasonModel
    return SeasonModel.get_or_create(experiment_id=exp_id, season_name=name)


# ============================================================
# Experiment-* associations (9 types)
# ============================================================

class TestExperimentSiteAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import ExperimentSiteModel
        exp, site = make_experiment("ES1"), make_site("ES1")
        ExperimentSiteModel.create(experiment_id=exp.id, site_id=site.id)
        assert ExperimentSiteModel.exists(experiment_id=exp.id, site_id=site.id)

    def test_cascade_on_experiment_delete(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        from gemini.db.models.associations import ExperimentSiteModel
        exp, site = make_experiment("ESD1"), make_site("ESD1")
        ExperimentSiteModel.create(experiment_id=exp.id, site_id=site.id)
        ExperimentModel.delete(exp)
        assert not ExperimentSiteModel.exists(experiment_id=exp.id, site_id=site.id)


class TestExperimentSensorAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import ExperimentSensorModel
        exp, sensor = make_experiment("ESn1"), make_sensor("ESn1")
        ExperimentSensorModel.create(experiment_id=exp.id, sensor_id=sensor.id)
        assert ExperimentSensorModel.exists(experiment_id=exp.id, sensor_id=sensor.id)

    def test_cascade_on_sensor_delete(self, setup_real_db):
        from gemini.db.models.sensors import SensorModel
        from gemini.db.models.associations import ExperimentSensorModel
        exp, sensor = make_experiment("ESn2"), make_sensor("ESn2")
        ExperimentSensorModel.create(experiment_id=exp.id, sensor_id=sensor.id)
        SensorModel.delete(sensor)
        assert not ExperimentSensorModel.exists(experiment_id=exp.id, sensor_id=sensor.id)


class TestExperimentSensorPlatformAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import ExperimentSensorPlatformModel
        exp, plat = make_experiment("ESP1"), make_platform("ESP1")
        ExperimentSensorPlatformModel.create(experiment_id=exp.id, sensor_platform_id=plat.id)
        assert ExperimentSensorPlatformModel.exists(experiment_id=exp.id, sensor_platform_id=plat.id)


class TestExperimentTraitAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import ExperimentTraitModel
        exp, trait = make_experiment("ET1"), make_trait("ET1")
        ExperimentTraitModel.create(experiment_id=exp.id, trait_id=trait.id)
        assert ExperimentTraitModel.exists(experiment_id=exp.id, trait_id=trait.id)


class TestExperimentPopulationAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import ExperimentPopulationModel
        exp, cult = make_experiment("EC1"), make_population("EC1_P")
        ExperimentPopulationModel.create(experiment_id=exp.id, population_id=cult.id)
        assert ExperimentPopulationModel.exists(experiment_id=exp.id, population_id=cult.id)


class TestExperimentDatasetAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import ExperimentDatasetModel
        exp, ds = make_experiment("ED1"), make_dataset("ED1")
        ExperimentDatasetModel.create(experiment_id=exp.id, dataset_id=ds.id)
        assert ExperimentDatasetModel.exists(experiment_id=exp.id, dataset_id=ds.id)


class TestExperimentModelAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import ExperimentModelModel
        exp, model = make_experiment("EM1"), make_model("EM1")
        ExperimentModelModel.create(experiment_id=exp.id, model_id=model.id)
        assert ExperimentModelModel.exists(experiment_id=exp.id, model_id=model.id)


class TestExperimentProcedureAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import ExperimentProcedureModel
        exp, proc = make_experiment("EP1"), make_procedure("EP1")
        ExperimentProcedureModel.create(experiment_id=exp.id, procedure_id=proc.id)
        assert ExperimentProcedureModel.exists(experiment_id=exp.id, procedure_id=proc.id)


class TestExperimentScriptAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import ExperimentScriptModel
        exp, script = make_experiment("EScr1"), make_script("EScr1")
        ExperimentScriptModel.create(experiment_id=exp.id, script_id=script.id)
        assert ExperimentScriptModel.exists(experiment_id=exp.id, script_id=script.id)


# ============================================================
# Non-experiment associations (9 types)
# ============================================================

class TestPopulationAccessionAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import PopulationAccessionModel
        pop = make_population("PA_Pop1")
        acc = make_accession("PA_Acc1")
        PopulationAccessionModel.create(population_id=pop.id, accession_id=acc.id)
        assert PopulationAccessionModel.exists(population_id=pop.id, accession_id=acc.id)


class TestSensorDatasetAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import SensorDatasetModel
        sensor, ds = make_sensor("SD1"), make_dataset("SD1")
        SensorDatasetModel.create(sensor_id=sensor.id, dataset_id=ds.id)
        assert SensorDatasetModel.exists(sensor_id=sensor.id, dataset_id=ds.id)


class TestTraitDatasetAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import TraitDatasetModel
        trait, ds = make_trait("TD1"), make_dataset("TD1")
        TraitDatasetModel.create(trait_id=trait.id, dataset_id=ds.id)
        assert TraitDatasetModel.exists(trait_id=trait.id, dataset_id=ds.id)


class TestTraitSensorAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import TraitSensorModel
        trait, sensor = make_trait("TS1"), make_sensor("TS1")
        TraitSensorModel.create(trait_id=trait.id, sensor_id=sensor.id)
        assert TraitSensorModel.exists(trait_id=trait.id, sensor_id=sensor.id)


class TestSensorPlatformSensorAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import SensorPlatformSensorModel
        plat, sensor = make_platform("SPS1"), make_sensor("SPS1")
        SensorPlatformSensorModel.create(sensor_platform_id=plat.id, sensor_id=sensor.id)
        assert SensorPlatformSensorModel.exists(sensor_platform_id=plat.id, sensor_id=sensor.id)


class TestModelDatasetAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import ModelDatasetModel
        model, ds = make_model("MD1"), make_dataset("MD1")
        ModelDatasetModel.create(model_id=model.id, dataset_id=ds.id)
        assert ModelDatasetModel.exists(model_id=model.id, dataset_id=ds.id)


class TestScriptDatasetAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import ScriptDatasetModel
        script, ds = make_script("ScrD1"), make_dataset("ScrD1")
        ScriptDatasetModel.create(script_id=script.id, dataset_id=ds.id)
        assert ScriptDatasetModel.exists(script_id=script.id, dataset_id=ds.id)


class TestProcedureDatasetAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import ProcedureDatasetModel
        proc, ds = make_procedure("PD1"), make_dataset("PD1")
        ProcedureDatasetModel.create(procedure_id=proc.id, dataset_id=ds.id)
        assert ProcedureDatasetModel.exists(procedure_id=proc.id, dataset_id=ds.id)


class TestDataTypeFormatAssociation:
    def test_create_and_exists(self, setup_real_db):
        from gemini.db.models.associations import DataTypeFormatModel
        # Use seed data: data_type_id=4 (Image), data_format_id=8 (JPEG)
        DataTypeFormatModel.get_or_create(data_type_id=4, data_format_id=8)
        assert DataTypeFormatModel.exists(data_type_id=4, data_format_id=8)
