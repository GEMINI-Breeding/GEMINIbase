"""
Tests for gemini.db.models.sites.SiteModel schema definition.
"""
import pytest
from sqlalchemy.schema import UniqueConstraint

from gemini.db.models.sites import SiteModel


class TestSiteModelSchema:
    """Verify SiteModel table metadata and column definitions."""

    def test_tablename(self):
        assert SiteModel.__tablename__ == "sites"

    def test_has_id_column(self):
        assert "id" in SiteModel.__table__.columns

    def test_has_site_name_column(self):
        assert "site_name" in SiteModel.__table__.columns

    def test_has_site_city_column(self):
        assert "site_city" in SiteModel.__table__.columns

    def test_has_site_state_column(self):
        assert "site_state" in SiteModel.__table__.columns

    def test_has_site_country_column(self):
        assert "site_country" in SiteModel.__table__.columns

    def test_has_site_info_column(self):
        assert "site_info" in SiteModel.__table__.columns

    def test_has_created_at_column(self):
        assert "created_at" in SiteModel.__table__.columns

    def test_has_updated_at_column(self):
        assert "updated_at" in SiteModel.__table__.columns

    def test_id_is_primary_key(self):
        assert SiteModel.__table__.columns["id"].primary_key

    def test_site_name_not_nullable(self):
        assert SiteModel.__table__.columns["site_name"].nullable is False

    def test_unique_constraint_exists(self):
        unique_constraints = [
            c
            for c in SiteModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        assert len(unique_constraints) >= 1
        # The composite unique constraint should include these four columns
        col_names = set()
        for uc in unique_constraints:
            for col in uc.columns:
                col_names.add(col.name)
        assert {"site_name", "site_city", "site_state", "site_country"}.issubset(
            col_names
        )

    def test_gin_index_on_site_info(self):
        index_names = [idx.name for idx in SiteModel.__table__.indexes]
        assert "idx_sites_info" in index_names

    def test_site_info_column_type_is_jsonb(self):
        from sqlalchemy.dialects.postgresql import JSONB

        col = SiteModel.__table__.columns["site_info"]
        assert isinstance(col.type, JSONB)

    def test_column_count(self):
        # id, site_name, site_city, site_state, site_country, site_info, created_at, updated_at
        assert len(SiteModel.__table__.columns) == 8

    def test_schema_is_gemini(self):
        assert SiteModel.__table__.schema == "gemini"
