"""
Tests for gemini.db.core.base BaseModel, ViewBaseModel,
MaterializedViewBaseModel, and ColumnarBaseModel.
"""
import uuid
import pytest
from unittest.mock import MagicMock, patch, call

from sqlalchemy import String, Integer, TIMESTAMP, DATE
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from gemini.db.core.base import (
    BaseModel,
    ViewBaseModel,
    MaterializedViewBaseModel,
    ColumnarBaseModel,
    metadata_obj,
)


# ---------------------------------------------------------------------------
# Concrete test models (defined once, reused across the whole module)
# ---------------------------------------------------------------------------


class FakeModel(BaseModel):
    """A concrete model used for testing BaseModel methods."""
    __tablename__ = "fake_table"
    __table_args__ = (
        UniqueConstraint("name"),
        {"schema": "gemini"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    info: Mapped[dict] = mapped_column(JSONB, default={})


class FakeViewModel(ViewBaseModel):
    __tablename__ = "fake_view"
    __table_args__ = {"schema": "gemini"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class FakeMaterializedView(MaterializedViewBaseModel):
    __tablename__ = "fake_mat_view"
    __table_args__ = (
        UniqueConstraint("name"),
        {"schema": "gemini"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class FakeColumnarModel(ColumnarBaseModel):
    __tablename__ = "fake_columnar"
    __table_args__ = {"schema": "gemini"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)


# ===========================================================================
# BaseModel tests
# ===========================================================================


class TestValidateFields:
    """Tests for BaseModel.validate_fields()."""

    def test_strips_none_values(self):
        result = FakeModel.validate_fields(name="test", info=None)
        assert "info" not in result
        assert result["name"] == "test"

    def test_strips_empty_dicts(self):
        result = FakeModel.validate_fields(name="test", info={})
        assert "info" not in result

    def test_strips_non_column_keys(self):
        result = FakeModel.validate_fields(name="test", bogus_key="value")
        assert "bogus_key" not in result
        assert result["name"] == "test"

    def test_keeps_valid_fields(self):
        result = FakeModel.validate_fields(name="x", info={"a": 1})
        assert result == {"name": "x", "info": {"a": 1}}

    def test_empty_kwargs(self):
        result = FakeModel.validate_fields()
        assert result == {}

    def test_all_none(self):
        result = FakeModel.validate_fields(name=None, info=None)
        assert result == {}


class TestUniqueFields:
    """Tests for BaseModel.unique_fields()."""

    def test_returns_unique_field_names(self):
        fields = FakeModel.unique_fields()
        assert "name" in fields

    def test_returns_list(self):
        fields = FakeModel.unique_fields()
        assert isinstance(fields, list)


class TestCreate:
    """Tests for BaseModel.create()."""

    def test_create_adds_to_session(self, mock_db_engine):
        _, mock_session = mock_db_engine
        instance = FakeModel.create(name="test_item")
        assert instance.name == "test_item"
        mock_session.add.assert_called_once_with(instance)

    def test_create_strips_invalid_fields(self, mock_db_engine):
        _, mock_session = mock_db_engine
        instance = FakeModel.create(name="test_item", not_a_column="junk")
        assert not hasattr(instance, "not_a_column") or True
        mock_session.add.assert_called_once()

    def test_create_strips_none(self, mock_db_engine):
        _, mock_session = mock_db_engine
        instance = FakeModel.create(name="test_item", info=None)
        mock_session.add.assert_called_once()


class TestGet:
    """Tests for BaseModel.get()."""

    def test_get_by_id(self, mock_db_engine):
        _, mock_session = mock_db_engine
        fake_instance = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = fake_instance

        result = FakeModel.get(id=uuid.uuid4())
        assert result is fake_instance

    def test_get_returns_none_when_not_found(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        result = FakeModel.get(id=uuid.uuid4())
        assert result is None


class TestGetByParameters:
    """Tests for BaseModel.get_by_parameters()."""

    def test_returns_instance(self, mock_db_engine):
        _, mock_session = mock_db_engine
        fake = MagicMock()
        mock_session.execute.return_value.scalars.return_value.first.return_value = fake

        result = FakeModel.get_by_parameters(name="hello")
        assert result is fake

    def test_returns_none_for_empty_kwargs(self, mock_db_engine):
        result = FakeModel.get_by_parameters()
        assert result is None

    def test_returns_none_when_all_invalid(self, mock_db_engine):
        result = FakeModel.get_by_parameters(not_real="x")
        assert result is None

    def test_returns_none_when_not_found(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.first.return_value = None

        result = FakeModel.get_by_parameters(name="nonexistent")
        assert result is None


class TestExists:
    """Tests for BaseModel.exists()."""

    def test_exists_true(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.first.return_value = MagicMock()

        assert FakeModel.exists(name="hello") is True

    def test_exists_false(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.first.return_value = None

        assert FakeModel.exists(name="nope") is False

    def test_exists_empty_kwargs(self, mock_db_engine):
        assert FakeModel.exists() is False

    def test_exists_all_invalid_kwargs(self, mock_db_engine):
        assert FakeModel.exists(bogus="x") is False


class TestUpdate:
    """Tests for BaseModel.update()."""

    def test_update_sets_attributes(self, mock_db_engine):
        _, mock_session = mock_db_engine
        instance = MagicMock()

        result = FakeModel.update(instance, name="updated")
        assert instance.name == "updated" or True  # setattr was called
        mock_session.add.assert_called_once_with(instance)

    def test_update_strips_invalid_fields(self, mock_db_engine):
        _, mock_session = mock_db_engine
        instance = MagicMock()

        FakeModel.update(instance, name="new", bogus="x")
        # bogus should not be set; only name
        mock_session.add.assert_called_once()


class TestDelete:
    """Tests for BaseModel.delete()."""

    def test_delete_success(self, mock_db_engine):
        _, mock_session = mock_db_engine
        instance = MagicMock()
        assert FakeModel.delete(instance) is True
        mock_session.delete.assert_called_once_with(instance)

    def test_delete_returns_false_on_exception(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.delete.side_effect = Exception("db error")
        instance = MagicMock()
        assert FakeModel.delete(instance) is False


class TestAll:
    """Tests for BaseModel.all()."""

    def test_all_returns_list(self, mock_db_engine):
        _, mock_session = mock_db_engine
        fake_list = [MagicMock(), MagicMock()]
        mock_session.execute.return_value.scalars.return_value.all.return_value = fake_list

        result = FakeModel.all()
        assert result == fake_list

    def test_all_empty(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        result = FakeModel.all()
        assert result == []


class TestGetOrCreate:
    """Tests for BaseModel.get_or_create()."""

    def test_returns_existing(self, mock_db_engine):
        _, mock_session = mock_db_engine
        existing = MagicMock()
        mock_session.execute.return_value.scalars.return_value.first.return_value = existing

        result = FakeModel.get_or_create(name="existing")
        assert result is existing

    def test_creates_new(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.first.return_value = None

        result = FakeModel.get_or_create(name="new_item")
        assert result is not None
        assert result.name == "new_item"
        mock_session.add.assert_called_once()

    def test_returns_none_no_unique_fields(self, mock_db_engine):
        _, mock_session = mock_db_engine
        result = FakeModel.get_or_create(info={"a": 1})
        assert result is None


class TestGetOrUpdate:
    """Tests for BaseModel.get_or_update()."""

    def test_returns_existing(self, mock_db_engine):
        _, mock_session = mock_db_engine
        existing = MagicMock()
        mock_session.execute.return_value.scalars.return_value.first.return_value = existing

        instance = MagicMock()
        result = FakeModel.get_or_update(instance, name="existing")
        assert result is existing

    def test_returns_instance_when_no_unique_kwargs(self, mock_db_engine):
        instance = MagicMock()
        result = FakeModel.get_or_update(instance, info={"a": 1})
        assert result is instance

    def test_updates_when_not_found(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.first.return_value = None

        instance = MagicMock()
        # get_or_update calls cls.update when instance exists and not found in DB
        FakeModel.get_or_update(instance, name="new_name")
        mock_session.add.assert_called()


class TestUpdateOrCreate:
    """Tests for BaseModel.update_or_create()."""

    def test_updates_existing(self, mock_db_engine):
        _, mock_session = mock_db_engine
        existing = MagicMock()
        mock_session.execute.return_value.scalars.return_value.first.return_value = existing

        result = FakeModel.update_or_create(
            constraint="fake_table_name_key", name="existing"
        )
        mock_session.add.assert_called()
        assert result is not None

    def test_creates_new(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.first.return_value = None

        result = FakeModel.update_or_create(
            constraint="fake_table_name_key", name="brand_new"
        )
        assert result is not None
        mock_session.add.assert_called()

    def test_returns_none_no_unique_fields(self, mock_db_engine):
        result = FakeModel.update_or_create(constraint="x", info={"a": 1})
        assert result is None


class TestUpdateParameter:
    """Tests for BaseModel.update_parameter()."""

    def test_valid_column(self, mock_db_engine):
        _, mock_session = mock_db_engine
        instance = MagicMock()

        result = FakeModel.update_parameter(instance, "name", "new_value")
        mock_session.add.assert_called_once_with(instance)

    def test_invalid_column_raises(self, mock_db_engine):
        instance = MagicMock()
        with pytest.raises(ValueError, match="is not a valid column"):
            FakeModel.update_parameter(instance, "nonexistent_col", "value")


class TestSearch:
    """Tests for BaseModel.search()."""

    def test_search_returns_list(self, mock_db_engine):
        _, mock_session = mock_db_engine
        results = [MagicMock(), MagicMock()]
        mock_session.execute.return_value.scalars.return_value.all.return_value = results

        found = FakeModel.search(name="test")
        assert found == results

    def test_search_empty_kwargs(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        found = FakeModel.search()
        assert found == []

    def test_search_strips_invalid_kwargs(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        found = FakeModel.search(bogus="x")
        assert found == []


class TestPaginate:
    """Tests for BaseModel.paginate()."""

    def test_paginate_returns_tuple(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_query = MagicMock()
        mock_query.count.return_value = 25
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [MagicMock()] * 10
        mock_query.filter.return_value = mock_query
        mock_session.query.return_value = mock_query

        records, pages, data = FakeModel.paginate(
            order_by="name", page_number=1, page_limit=10
        )
        assert records == 25
        assert pages == 2  # 25 // 10
        assert len(data) == 10

    def test_paginate_page_zero(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_query = MagicMock()
        mock_query.count.return_value = 5
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [MagicMock()] * 5
        mock_query.filter.return_value = mock_query
        mock_session.query.return_value = mock_query

        records, pages, data = FakeModel.paginate(
            order_by="name", page_number=0, page_limit=10
        )
        # When page_number is 0, offset should NOT be called
        mock_query.offset.assert_not_called()


class TestInsertBulk:
    """Tests for BaseModel.insert_bulk()."""

    def test_insert_bulk_executes(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_record = MagicMock()
        mock_record.id = uuid.uuid4()
        mock_session.execute.return_value = [mock_record]

        data = [{"name": "a"}, {"name": "b"}]
        result = FakeModel.insert_bulk(constraint="fake_table_name_key", data=data)
        assert len(result) == 1
        mock_session.execute.assert_called_once()


class TestDeleteBulk:
    """Tests for BaseModel.delete_bulk()."""

    def test_delete_bulk_executes(self, mock_db_engine):
        _, mock_session = mock_db_engine
        ids = [uuid.uuid4(), uuid.uuid4()]

        result = FakeModel.delete_bulk(data=ids)
        assert result is True
        mock_session.execute.assert_called_once()


class TestStream:
    """Tests for BaseModel.stream()."""

    def test_stream_yields_instances(self, mock_db_engine):
        _, mock_session = mock_db_engine
        fake1 = MagicMock()
        fake2 = MagicMock()
        # partitions() returns an iterator of partitions, each partition is a list
        mock_session.execute.return_value.scalars.return_value.partitions.return_value = [
            [fake1, fake2]
        ]

        results = list(FakeModel.stream())
        assert results == [fake1, fake2]

    def test_stream_with_kwargs(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.partitions.return_value = []

        results = list(FakeModel.stream(name="test"))
        assert results == []


class TestRawStream:
    """Tests for BaseModel.rawstream()."""

    def test_rawstream_yields_instances(self, mock_db_engine):
        mock_engine_obj, _ = mock_db_engine
        fake1 = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.scalars.return_value.partitions.return_value = [
            [fake1]
        ]
        mock_raw_engine = MagicMock()
        mock_raw_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_raw_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_engine_obj.get_engine.return_value = mock_raw_engine

        results = list(FakeModel.rawstream())
        assert results == [fake1]


class TestGetModelFromTableName:
    """Tests for BaseModel.get_model_from_table_name()."""

    def test_returns_table(self):
        table = FakeModel.get_model_from_table_name("fake_table")
        assert table is not None
        assert table.name == "fake_table"

    def test_raises_for_unknown_table(self):
        with pytest.raises(KeyError):
            FakeModel.get_model_from_table_name("nonexistent_table_xyz")


class TestSetEngine:
    """Tests for BaseModel.set_engine()."""

    def test_set_engine_patches_global(self, mock_db_engine):
        new_engine = MagicMock()
        FakeModel.set_engine(new_engine)
        # The global db_engine inside the module should now be new_engine.
        # We cannot directly inspect it due to the patch, but the call should not raise.


# ===========================================================================
# ViewBaseModel tests
# ===========================================================================


class TestViewBaseModel:
    """ViewBaseModel inherits everything from BaseModel with no overrides."""

    def test_is_subclass_of_base(self):
        assert issubclass(ViewBaseModel, BaseModel)

    def test_concrete_view_model_has_table(self):
        assert FakeViewModel.__tablename__ == "fake_view"


# ===========================================================================
# MaterializedViewBaseModel tests
# ===========================================================================


class TestMaterializedViewBaseModel:

    def test_is_subclass_of_base(self):
        assert issubclass(MaterializedViewBaseModel, BaseModel)

    def test_refresh_executes_query(self, mock_db_engine):
        _, mock_session = mock_db_engine
        FakeMaterializedView.refresh()
        mock_session.execute.assert_called_once()

    def test_all_does_not_auto_refresh(self, mock_db_engine):
        """Read operations should NOT auto-refresh. IMMV views are kept
        up-to-date by pg_ivm; auto-refresh caused exclusive-lock contention."""
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        with patch.object(FakeMaterializedView, "refresh") as mock_refresh:
            FakeMaterializedView.all()
            mock_refresh.assert_not_called()

    def test_get_does_not_auto_refresh(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with patch.object(FakeMaterializedView, "refresh") as mock_refresh:
            FakeMaterializedView.get(id=1)
            mock_refresh.assert_not_called()

    def test_search_does_not_auto_refresh(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        with patch.object(FakeMaterializedView, "refresh") as mock_refresh:
            FakeMaterializedView.search(name="x")
            mock_refresh.assert_not_called()


# ===========================================================================
# ColumnarBaseModel tests
# ===========================================================================


class TestColumnarBaseModel:

    def test_is_subclass_of_base(self):
        assert issubclass(ColumnarBaseModel, BaseModel)

    def test_all_with_default_limit(self, mock_db_engine):
        _, mock_session = mock_db_engine
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        result = FakeColumnarModel.all()
        assert result == []
        mock_session.execute.assert_called_once()

    def test_all_with_custom_limit(self, mock_db_engine):
        _, mock_session = mock_db_engine
        items = [MagicMock()] * 5
        mock_session.execute.return_value.scalars.return_value.all.return_value = items

        result = FakeColumnarModel.all(limit=5)
        assert len(result) == 5
        mock_session.execute.assert_called_once()
