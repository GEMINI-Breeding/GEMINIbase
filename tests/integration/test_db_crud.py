"""
Integration tests for database CRUD operations against real PostgreSQL.

Requires: docker compose -f tests/docker-compose.test.yaml up -d
Run with: pytest tests/integration/ -v -m integration
"""
import pytest
from datetime import date

pytestmark = pytest.mark.integration


class TestExperimentCRUD:

    def test_create_experiment(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        exp = ExperimentModel.create(
            experiment_name="Test Experiment",
            experiment_info={"crop": "wheat"},
        )
        assert exp is not None
        assert exp.experiment_name == "Test Experiment"
        assert exp.id is not None

    def test_get_experiment_by_name(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        ExperimentModel.create(experiment_name="Find Me")
        found = ExperimentModel.get_by_parameters(experiment_name="Find Me")
        assert found is not None
        assert found.experiment_name == "Find Me"

    def test_get_or_create_returns_existing(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        first = ExperimentModel.get_or_create(experiment_name="Idempotent")
        second = ExperimentModel.get_or_create(experiment_name="Idempotent")
        assert str(first.id) == str(second.id)

    def test_update_experiment(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        exp = ExperimentModel.create(experiment_name="Update Me")
        updated = ExperimentModel.update(exp, experiment_info={"updated": True})
        assert updated.experiment_info == {"updated": True}

        # Verify persisted
        fetched = ExperimentModel.get_by_parameters(experiment_name="Update Me")
        assert fetched.experiment_info == {"updated": True}

    def test_delete_experiment(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        exp = ExperimentModel.create(experiment_name="Delete Me")
        exp_id = exp.id
        assert ExperimentModel.delete(exp) is True
        assert ExperimentModel.get(exp_id) is None

    def test_all_with_pagination(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        for i in range(5):
            ExperimentModel.create(experiment_name=f"Exp {i}")

        all_results = ExperimentModel.all()
        assert len(all_results) == 5

        page = ExperimentModel.all(limit=2, offset=0)
        assert len(page) == 2

        page2 = ExperimentModel.all(limit=2, offset=2)
        assert len(page2) == 2

    def test_count(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        assert ExperimentModel.count() == 0
        ExperimentModel.create(experiment_name="Count Test")
        assert ExperimentModel.count() == 1

    def test_search(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        ExperimentModel.create(experiment_name="Search A")
        ExperimentModel.create(experiment_name="Search B")

        results = ExperimentModel.search(experiment_name="Search A")
        assert len(results) == 1
        assert results[0].experiment_name == "Search A"

    def test_exists(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        assert ExperimentModel.exists(experiment_name="Ghost") is False
        ExperimentModel.create(experiment_name="Ghost")
        assert ExperimentModel.exists(experiment_name="Ghost") is True

    def test_unique_constraint_enforced(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        ExperimentModel.create(experiment_name="Unique")
        # get_or_create should return existing, not raise
        second = ExperimentModel.get_or_create(experiment_name="Unique")
        assert second is not None
        assert ExperimentModel.count() == 1


class TestSiteCRUD:

    def test_create_and_get(self, setup_real_db):
        from gemini.db.models.sites import SiteModel

        site = SiteModel.create(
            site_name="Davis", site_city="Davis",
            site_state="CA", site_country="USA"
        )
        assert site.id is not None

        fetched = SiteModel.get(site.id)
        assert fetched.site_name == "Davis"

    def test_jsonb_info_stored(self, setup_real_db):
        from gemini.db.models.sites import SiteModel

        site = SiteModel.create(
            site_name="InfoTest", site_city="City",
            site_state="ST", site_country="US",
            site_info={"lat": 38.54, "lon": -121.74}
        )
        fetched = SiteModel.get(site.id)
        assert fetched.site_info["lat"] == 38.54


class TestAssociations:

    def test_experiment_site_association(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        from gemini.db.models.sites import SiteModel
        from gemini.db.models.associations import ExperimentSiteModel

        exp = ExperimentModel.create(experiment_name="Assoc Exp")
        site = SiteModel.create(
            site_name="Assoc Site", site_city="C",
            site_state="S", site_country="US"
        )

        assoc = ExperimentSiteModel.create(
            experiment_id=exp.id, site_id=site.id
        )
        assert assoc is not None

        # Verify the association exists
        assert ExperimentSiteModel.exists(
            experiment_id=exp.id, site_id=site.id
        ) is True

    def test_cascade_delete_removes_association(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        from gemini.db.models.sites import SiteModel
        from gemini.db.models.associations import ExperimentSiteModel

        exp = ExperimentModel.create(experiment_name="Cascade Exp")
        site = SiteModel.create(
            site_name="Cascade Site", site_city="C",
            site_state="S", site_country="US"
        )
        ExperimentSiteModel.create(experiment_id=exp.id, site_id=site.id)

        # Delete experiment — should cascade to association
        ExperimentModel.delete(exp)
        assert ExperimentSiteModel.exists(
            experiment_id=exp.id, site_id=site.id
        ) is False


class TestSeasonExperimentRelationship:

    def test_season_requires_experiment(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        from gemini.db.models.seasons import SeasonModel

        exp = ExperimentModel.create(experiment_name="Season Exp")
        season = SeasonModel.create(
            experiment_id=exp.id,
            season_name="2024",
        )
        assert season is not None
        assert season.experiment_id == exp.id

    def test_cascade_deletes_seasons(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        from gemini.db.models.seasons import SeasonModel

        exp = ExperimentModel.create(experiment_name="Del Season Exp")
        SeasonModel.create(experiment_id=exp.id, season_name="2024")

        ExperimentModel.delete(exp)
        seasons = SeasonModel.search(season_name="2024")
        assert len(seasons) == 0


class TestPlotHierarchy:

    def test_create_full_hierarchy(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        from gemini.db.models.seasons import SeasonModel
        from gemini.db.models.sites import SiteModel
        from gemini.db.models.plots import PlotModel
        from gemini.db.models.associations import ExperimentSiteModel

        exp = ExperimentModel.create(experiment_name="Hierarchy Exp")
        season = SeasonModel.create(experiment_id=exp.id, season_name="2024")
        site = SiteModel.create(
            site_name="Hierarchy Site", site_city="C",
            site_state="S", site_country="US"
        )
        ExperimentSiteModel.create(experiment_id=exp.id, site_id=site.id)

        plot = PlotModel.create(
            experiment_id=exp.id, season_id=season.id, site_id=site.id,
            plot_number=1, plot_row_number=1, plot_column_number=1
        )
        assert plot is not None
        assert plot.experiment_id == exp.id
        assert plot.season_id == season.id
        assert plot.site_id == site.id


class TestBulkOperations:

    def test_insert_bulk(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        import uuid

        data = [
            {"id": str(uuid.uuid4()), "experiment_name": f"Bulk {i}"}
            for i in range(10)
        ]
        ids = ExperimentModel.insert_bulk(
            constraint="experiment_unique", data=data
        )
        assert len(ids) == 10
        assert ExperimentModel.count() == 10

    def test_insert_bulk_ignores_duplicates(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        ExperimentModel.create(experiment_name="Existing")
        import uuid
        data = [
            {"id": str(uuid.uuid4()), "experiment_name": "Existing"},
            {"id": str(uuid.uuid4()), "experiment_name": "New One"},
        ]
        ids = ExperimentModel.insert_bulk(
            constraint="experiment_unique", data=data
        )
        # Only "New One" should be inserted
        assert len(ids) == 1
        assert ExperimentModel.count() == 2

    def test_delete_bulk(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        exps = [
            ExperimentModel.create(experiment_name=f"DelBulk {i}")
            for i in range(3)
        ]
        ids = [e.id for e in exps]
        assert ExperimentModel.delete_bulk(ids) is True
        assert ExperimentModel.count() == 0


class TestStreamOperations:

    def test_stream(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel

        for i in range(5):
            ExperimentModel.create(experiment_name=f"Stream {i}")

        streamed = list(ExperimentModel.stream())
        assert len(streamed) == 5
