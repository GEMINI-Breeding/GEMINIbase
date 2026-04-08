"""Unit tests for the Variant API class."""

from unittest.mock import patch, MagicMock
from uuid import uuid4
from gemini.api.variant import Variant

MODULE = "gemini.api.variant"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(),
        "variant_name": "2_24641",
        "chromosome": 1,
        "position": 0.0,
        "alleles": "T/C",
        "design_sequence": "AGAC[T/C]GACT",
        "variant_info": {"key": "val"},
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestVariantExists:
    @patch(f"{MODULE}.VariantModel")
    def test_exists_true(self, m):
        m.exists.return_value = True
        assert Variant.exists(variant_name="2_24641") is True

    @patch(f"{MODULE}.VariantModel")
    def test_exists_false(self, m):
        m.exists.return_value = False
        assert Variant.exists(variant_name="nonexistent") is False

    @patch(f"{MODULE}.VariantModel")
    def test_exists_exception(self, m):
        m.exists.side_effect = Exception("DB error")
        assert Variant.exists(variant_name="2_24641") is False


class TestVariantCreate:
    @patch(f"{MODULE}.VariantModel")
    def test_create_success(self, m):
        m.get_or_create.return_value = _make_db()
        result = Variant.create(variant_name="2_24641", chromosome=1, position=0.0, alleles="T/C")
        assert result is not None
        assert result.variant_name == "2_24641"

    @patch(f"{MODULE}.VariantModel")
    def test_create_exception(self, m):
        m.get_or_create.side_effect = Exception("DB error")
        result = Variant.create(variant_name="2_24641", chromosome=1, position=0.0, alleles="T/C")
        assert result is None


class TestVariantCreateBulk:
    @patch(f"{MODULE}.VariantModel")
    def test_bulk_success(self, m):
        m.insert_bulk.return_value = [uuid4(), uuid4()]
        success, ids = Variant.create_bulk([{"variant_name": "a"}, {"variant_name": "b"}])
        assert success is True
        assert len(ids) == 2

    @patch(f"{MODULE}.VariantModel")
    def test_bulk_empty(self, m):
        success, ids = Variant.create_bulk([])
        assert success is False
        assert ids == []

    @patch(f"{MODULE}.VariantModel")
    def test_bulk_exception(self, m):
        m.insert_bulk.side_effect = Exception("DB error")
        success, ids = Variant.create_bulk([{"variant_name": "a"}])
        assert success is False


class TestVariantGet:
    @patch(f"{MODULE}.VariantModel")
    def test_get_success(self, m):
        m.get_by_parameters.return_value = _make_db()
        result = Variant.get(variant_name="2_24641")
        assert result is not None
        assert result.variant_name == "2_24641"

    @patch(f"{MODULE}.VariantModel")
    def test_get_not_found(self, m):
        m.get_by_parameters.return_value = None
        result = Variant.get(variant_name="nonexistent")
        assert result is None

    @patch(f"{MODULE}.VariantModel")
    def test_get_exception(self, m):
        m.get_by_parameters.side_effect = Exception("DB error")
        result = Variant.get(variant_name="2_24641")
        assert result is None


class TestVariantGetById:
    @patch(f"{MODULE}.VariantModel")
    def test_get_by_id_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        result = Variant.get_by_id(uid)
        assert result is not None

    @patch(f"{MODULE}.VariantModel")
    def test_get_by_id_not_found(self, m):
        m.get.return_value = None
        result = Variant.get_by_id(uuid4())
        assert result is None


class TestVariantGetAll:
    @patch(f"{MODULE}.VariantModel")
    def test_get_all_success(self, m):
        m.all.return_value = [_make_db(), _make_db()]
        result = Variant.get_all()
        assert result is not None
        assert len(result) == 2

    @patch(f"{MODULE}.VariantModel")
    def test_get_all_empty(self, m):
        m.all.return_value = []
        result = Variant.get_all()
        assert result is None


class TestVariantSearch:
    @patch(f"{MODULE}.VariantModel")
    def test_search_success(self, m):
        m.search.return_value = [_make_db()]
        result = Variant.search(chromosome=1)
        assert result is not None
        assert len(result) == 1

    def test_search_no_params(self):
        result = Variant.search()
        assert result is None

    @patch(f"{MODULE}.VariantModel")
    def test_search_empty(self, m):
        m.search.return_value = []
        result = Variant.search(chromosome=99)
        assert result is None


class TestVariantUpdate:
    @patch(f"{MODULE}.VariantModel")
    def test_update_success(self, m):
        uid = uuid4()
        db_obj = _make_db(id=uid)
        m.get.return_value = db_obj
        m.update.return_value = _make_db(id=uid, chromosome=2)
        variant = Variant(variant_name="2_24641", chromosome=1, position=0.0, alleles="T/C", id=uid)
        result = variant.update(chromosome=2)
        assert result is not None

    @patch(f"{MODULE}.VariantModel")
    def test_update_no_params(self, m):
        variant = Variant(variant_name="2_24641", chromosome=1, position=0.0, alleles="T/C", id=uuid4())
        result = variant.update()
        assert result is None


class TestVariantDelete:
    @patch(f"{MODULE}.VariantModel")
    def test_delete_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.delete.return_value = True
        variant = Variant(variant_name="2_24641", chromosome=1, position=0.0, alleles="T/C", id=uid)
        assert variant.delete() is True

    @patch(f"{MODULE}.VariantModel")
    def test_delete_not_found(self, m):
        m.get.return_value = None
        variant = Variant(variant_name="2_24641", chromosome=1, position=0.0, alleles="T/C", id=uuid4())
        assert variant.delete() is False


class TestVariantRefresh:
    @patch(f"{MODULE}.VariantModel")
    def test_refresh_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid, chromosome=2)
        variant = Variant(variant_name="2_24641", chromosome=1, position=0.0, alleles="T/C", id=uid)
        result = variant.refresh()
        assert result is not None

    @patch(f"{MODULE}.VariantModel")
    def test_refresh_not_found(self, m):
        m.get.return_value = None
        variant = Variant(variant_name="2_24641", chromosome=1, position=0.0, alleles="T/C", id=uuid4())
        result = variant.refresh()
        assert result == variant


class TestVariantGetSetInfo:
    @patch(f"{MODULE}.VariantModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(variant_info={"key": "val"})
        variant = Variant(variant_name="2_24641", chromosome=1, position=0.0, alleles="T/C", id=uuid4())
        info = variant.get_info()
        assert info == {"key": "val"}

    @patch(f"{MODULE}.VariantModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, variant_info={"new": "val"})
        variant = Variant(variant_name="2_24641", chromosome=1, position=0.0, alleles="T/C", id=uid)
        result = variant.set_info({"new": "val"})
        assert result is not None
