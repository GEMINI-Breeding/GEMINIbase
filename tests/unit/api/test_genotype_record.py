"""Unit tests for the GenotypeRecord API class."""

from unittest.mock import patch, MagicMock
from uuid import uuid4
from gemini.api.genotype_record import GenotypeRecord

MODULE = "gemini.api.genotype_record"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(),
        "genotype_id": uuid4(),
        "genotype_name": "Cowpea_MAGIC_GBS",
        "variant_id": uuid4(),
        "variant_name": "2_24641",
        "chromosome": 1,
        "position": 0.0,
        "population_id": uuid4(),
        "population_name": "IT89KD-288",
        "population_accession": "IT89KD-288",
        "call_value": "TT",
        "record_info": {},
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestGenotypeRecordExists:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_exists_true(self, m):
        m.exists.return_value = True
        assert GenotypeRecord.exists(
            genotype_name="test", variant_name="2_24641", population_name="IT89KD-288"
        ) is True

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_exists_false(self, m):
        m.exists.return_value = False
        assert GenotypeRecord.exists(
            genotype_name="test", variant_name="x", population_name="y"
        ) is False


class TestGenotypeRecordInsert:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_insert_success(self, m):
        m.insert_bulk.return_value = [uuid4(), uuid4()]
        records = [
            GenotypeRecord(genotype_name="test", variant_name="a", population_name="p1", call_value="AA"),
            GenotypeRecord(genotype_name="test", variant_name="b", population_name="p1", call_value="TT"),
        ]
        success, ids = GenotypeRecord.insert(records)
        assert success is True
        assert len(ids) == 2

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_insert_empty(self, m):
        success, ids = GenotypeRecord.insert([])
        assert success is False

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_insert_exception(self, m):
        m.insert_bulk.side_effect = Exception("DB error")
        records = [GenotypeRecord(genotype_name="t", variant_name="v", population_name="p", call_value="AA")]
        success, ids = GenotypeRecord.insert(records)
        assert success is False


class TestGenotypeRecordGet:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_get_success(self, m):
        m.get_by_parameters.return_value = _make_db()
        result = GenotypeRecord.get(genotype_name="test", variant_name="2_24641", population_name="IT89KD-288")
        assert result is not None

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_get_not_found(self, m):
        m.get_by_parameters.return_value = None
        result = GenotypeRecord.get(genotype_name="test", variant_name="x", population_name="y")
        assert result is None


class TestGenotypeRecordGetById:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        result = GenotypeRecord.get_by_id(uid)
        assert result is not None

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert GenotypeRecord.get_by_id(uuid4()) is None


class TestGenotypeRecordGetAll:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_success(self, m):
        m.all.return_value = [_make_db(), _make_db()]
        result = GenotypeRecord.get_all()
        assert len(result) == 2

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert GenotypeRecord.get_all() is None


class TestGenotypeRecordSearch:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_success(self, m):
        m.search.return_value = [_make_db()]
        result = GenotypeRecord.search(genotype_name="test")
        assert result is not None

    def test_no_params(self):
        assert GenotypeRecord.search() is None


class TestGenotypeRecordFilter:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_filter_success(self, m):
        m.filter_records.return_value = iter([_make_db()])
        results = list(GenotypeRecord.filter(genotype_names=["test"]))
        assert len(results) == 1

    def test_filter_no_params(self):
        results = list(GenotypeRecord.filter())
        assert len(results) == 0


class TestGenotypeRecordUpdate:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, call_value="CC")
        r = GenotypeRecord(genotype_name="t", variant_name="v", population_name="p", call_value="AA", id=uid)
        result = r.update(call_value="CC")
        assert result is not None

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_no_params(self, m):
        r = GenotypeRecord(genotype_name="t", variant_name="v", population_name="p", call_value="AA", id=uuid4())
        assert r.update() is None


class TestGenotypeRecordDelete:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.delete.return_value = True
        r = GenotypeRecord(genotype_name="t", variant_name="v", population_name="p", call_value="AA", id=uid)
        assert r.delete() is True

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_not_found(self, m):
        m.get.return_value = None
        r = GenotypeRecord(genotype_name="t", variant_name="v", population_name="p", call_value="AA", id=uuid4())
        assert r.delete() is False
