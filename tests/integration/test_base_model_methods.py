"""
Integration tests for BaseModel methods that were fixed in Phase 1.
Proves the fixes actually work against real PostgreSQL.

Requires: docker compose -f tests/docker-compose.test.yaml up -d
"""
import pytest
import uuid

pytestmark = pytest.mark.integration


class TestUpdateBulk:
    """Tests update_bulk() — was broken before fix (stmt referenced before assignment)."""

    def test_upsert_updates_existing(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        # Create initial records
        ExperimentModel.create(experiment_name="Upsert A")
        ExperimentModel.create(experiment_name="Upsert B")

        # Upsert with updated info
        data = [
            {"id": str(uuid.uuid4()), "experiment_name": "Upsert A",
             "experiment_info": {"updated": True}},
            {"id": str(uuid.uuid4()), "experiment_name": "Upsert C",
             "experiment_info": {"new": True}},
        ]
        ids = ExperimentModel.update_bulk(
            constraint="experiment_unique",
            upsert_on="experiment_info",
            data=data
        )
        # Should have upserted both (1 update + 1 insert)
        assert len(ids) == 2

        # Verify the update happened
        a = ExperimentModel.get_by_parameters(experiment_name="Upsert A")
        assert a.experiment_info.get("updated") is True

        # Verify new insert
        c = ExperimentModel.get_by_parameters(experiment_name="Upsert C")
        assert c is not None


class TestGetOrUpdate:
    """Tests get_or_update() — was missing return statement before fix."""

    def test_returns_existing_when_found(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        exp = ExperimentModel.create(experiment_name="GetOrUpd Existing")
        result = ExperimentModel.get_or_update(
            None, experiment_name="GetOrUpd Existing"
        )
        assert result is not None
        assert str(result.id) == str(exp.id)

    def test_updates_instance_when_not_found(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        exp = ExperimentModel.create(experiment_name="GetOrUpd Update")
        result = ExperimentModel.get_or_update(
            exp, experiment_name="GetOrUpd Renamed"
        )
        assert result is not None

    def test_creates_new_when_no_instance(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        result = ExperimentModel.get_or_update(
            None, experiment_name="GetOrUpd New"
        )
        assert result is not None
        assert result.experiment_name == "GetOrUpd New"


class TestUpdateOrCreate:

    def test_creates_when_not_exists(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        result = ExperimentModel.update_or_create(
            constraint="experiment_unique",
            experiment_name="UoC New",
            experiment_info={"source": "test"}
        )
        assert result is not None
        assert result.experiment_name == "UoC New"

    def test_updates_when_exists(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        ExperimentModel.create(
            experiment_name="UoC Existing",
            experiment_info={"version": 1}
        )
        result = ExperimentModel.update_or_create(
            constraint="experiment_unique",
            experiment_name="UoC Existing",
            experiment_info={"version": 2}
        )
        assert result.experiment_info.get("version") == 2


class TestPaginateMethod:

    def test_paginate_returns_correct_pages(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        for i in range(15):
            ExperimentModel.create(experiment_name=f"Page Exp {i:02d}")

        total, pages, results = ExperimentModel.paginate(
            order_by="experiment_name", page_number=1, page_limit=5
        )
        assert total == 15
        assert pages == 3  # 15 // 5
        assert len(results) == 5

    def test_paginate_page_2(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        for i in range(10):
            ExperimentModel.create(experiment_name=f"P2 Exp {i}")

        total, pages, results = ExperimentModel.paginate(
            order_by="experiment_name", page_number=2, page_limit=3
        )
        assert total == 10
        assert len(results) == 3


class TestJSONBSearch:

    def test_jsonb_contains_search(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        ExperimentModel.create(
            experiment_name="JSONB A",
            experiment_info={"crop": "wheat", "year": 2024}
        )
        ExperimentModel.create(
            experiment_name="JSONB B",
            experiment_info={"crop": "rice", "year": 2024}
        )
        ExperimentModel.create(
            experiment_name="JSONB C",
            experiment_info={"crop": "wheat", "year": 2023}
        )

        # Search by JSONB contains
        results = ExperimentModel.search(experiment_info={"crop": "wheat"})
        assert len(results) == 2
        names = {r.experiment_name for r in results}
        assert "JSONB A" in names
        assert "JSONB C" in names

    def test_jsonb_contains_nested(self, setup_real_db):
        from gemini.db.models.sites import SiteModel
        SiteModel.create(
            site_name="GPS Site", site_city="Davis",
            site_state="CA", site_country="USA",
            site_info={"coordinates": {"lat": 38.54, "lon": -121.74}}
        )
        results = SiteModel.search(
            site_info={"coordinates": {"lat": 38.54, "lon": -121.74}}
        )
        assert len(results) == 1
        assert results[0].site_name == "GPS Site"


class TestCount:

    def test_count_empty(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        assert ExperimentModel.count() == 0

    def test_count_after_inserts(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        for i in range(7):
            ExperimentModel.create(experiment_name=f"Count {i}")
        assert ExperimentModel.count() == 7

    def test_count_after_delete(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        exps = [ExperimentModel.create(experiment_name=f"CDel {i}") for i in range(3)]
        ExperimentModel.delete(exps[0])
        assert ExperimentModel.count() == 2


class TestUpdateParameter:

    def test_update_single_field(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        exp = ExperimentModel.create(experiment_name="ParamUpd")
        ExperimentModel.update_parameter(
            exp, "experiment_info", {"status": "active"}
        )
        fetched = ExperimentModel.get(exp.id)
        assert fetched.experiment_info["status"] == "active"

    def test_rejects_invalid_column(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        exp = ExperimentModel.create(experiment_name="BadParam")
        with pytest.raises(ValueError, match="not a valid column"):
            ExperimentModel.update_parameter(exp, "nonexistent_field", "value")
