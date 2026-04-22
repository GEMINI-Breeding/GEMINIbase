"""Schema-level tests for the AccessionAliasModel — constraints, indexes, columns."""

import pytest
from sqlalchemy import CheckConstraint, Index

from gemini.db.models.accession_aliases import AccessionAliasModel


class TestAccessionAliasSchema:

    def test_tablename(self):
        assert AccessionAliasModel.__tablename__ == "accession_aliases"

    def test_has_required_columns(self):
        cols = set(AccessionAliasModel.__table__.columns.keys())
        assert {
            "id", "alias", "accession_id", "line_id",
            "scope", "experiment_id", "source", "alias_info",
            "created_at", "updated_at",
        }.issubset(cols)

    def test_check_constraints_declared(self):
        names = {
            c.name
            for c in AccessionAliasModel.__table__.constraints
            if isinstance(c, CheckConstraint)
        }
        assert {
            "accession_alias_scope_check",
            "accession_alias_target_check",
            "accession_alias_scope_experiment_check",
        }.issubset(names)

    def test_functional_indexes_declared(self):
        idx_names = {i.name for i in AccessionAliasModel.__table__.indexes}
        assert "idx_accession_aliases_lower_alias" in idx_names
        assert "idx_accession_aliases_exp_lower_alias" in idx_names
        assert "idx_accession_aliases_info" in idx_names

    def test_alias_non_nullable(self):
        assert AccessionAliasModel.__table__.c.alias.nullable is False

    def test_scope_default(self):
        assert AccessionAliasModel.__table__.c.scope.default.arg == "global"

    def test_accession_and_line_both_nullable(self):
        """FK nullability is enforced at the column level; mutual exclusion
        is the CHECK constraint's job."""
        assert AccessionAliasModel.__table__.c.accession_id.nullable is True
        assert AccessionAliasModel.__table__.c.line_id.nullable is True
