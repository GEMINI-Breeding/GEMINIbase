"""Tests for gemini.api.trait_level module - TraitLevel class."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.trait_level import TraitLevel

MODULE = "gemini.api.trait_level"


def _make_db(**overrides):
    defaults = {"id": uuid4(), "trait_level_name": "Plot", "trait_level_info": {"desc": "plot level"}}
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestTraitLevelExists:
    @patch(f"{MODULE}.TraitLevelModel")
    def test_true(self, m):
        m.exists.return_value = True
        assert TraitLevel.exists(trait_level_name="Plot") is True

    @patch(f"{MODULE}.TraitLevelModel")
    def test_false(self, m):
        m.exists.return_value = False
        assert TraitLevel.exists(trait_level_name="X") is False

    @patch(f"{MODULE}.TraitLevelModel")
    def test_exception(self, m):
        m.exists.side_effect = Exception("err")
        assert TraitLevel.exists(trait_level_name="X") is False


class TestTraitLevelCreate:
    @patch(f"{MODULE}.TraitLevelModel")
    def test_success(self, m):
        m.get_or_create.return_value = _make_db()
        assert TraitLevel.create(trait_level_name="Plot") is not None

    @patch(f"{MODULE}.TraitLevelModel")
    def test_exception(self, m):
        m.get_or_create.side_effect = Exception("err")
        assert TraitLevel.create(trait_level_name="X") is None


class TestTraitLevelGet:
    @patch(f"{MODULE}.TraitLevelModel")
    def test_found(self, m):
        m.get_by_parameters.return_value = _make_db()
        assert TraitLevel.get(trait_level_name="Plot") is not None

    @patch(f"{MODULE}.TraitLevelModel")
    def test_not_found(self, m):
        m.get_by_parameters.return_value = None
        assert TraitLevel.get(trait_level_name="X") is None


class TestTraitLevelGetById:
    @patch(f"{MODULE}.TraitLevelModel")
    def test_found(self, m):
        m.get.return_value = _make_db()
        assert TraitLevel.get_by_id(uuid4()) is not None

    @patch(f"{MODULE}.TraitLevelModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert TraitLevel.get_by_id(uuid4()) is None


class TestTraitLevelGetAll:
    @patch(f"{MODULE}.TraitLevelModel")
    def test_list(self, m):
        m.all.return_value = [_make_db()]
        assert len(TraitLevel.get_all()) == 1

    @patch(f"{MODULE}.TraitLevelModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert TraitLevel.get_all() is None


class TestTraitLevelSearch:
    @patch(f"{MODULE}.TraitLevelModel")
    def test_results(self, m):
        m.search.return_value = [_make_db()]
        assert len(TraitLevel.search(trait_level_name="Plot")) == 1

    def test_no_params(self):
        assert TraitLevel.search() is None

    @patch(f"{MODULE}.TraitLevelModel")
    def test_empty(self, m):
        m.search.return_value = []
        assert TraitLevel.search(trait_level_name="X") is None


class TestTraitLevelUpdate:
    @patch(f"{MODULE}.TraitLevelModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, trait_level_name="New")
        tl = TraitLevel(id=uid, trait_level_name="Old")
        assert tl.update(trait_level_name="New") is not None

    @patch(f"{MODULE}.TraitLevelModel")
    def test_no_params(self, m):
        tl = TraitLevel(id=uuid4(), trait_level_name="X")
        assert tl.update() is None

    @patch(f"{MODULE}.TraitLevelModel")
    def test_not_found(self, m):
        m.get.return_value = None
        tl = TraitLevel(id=uuid4(), trait_level_name="X")
        assert tl.update(trait_level_name="New") is None


class TestTraitLevelDelete:
    @patch(f"{MODULE}.TraitLevelModel")
    def test_success(self, m):
        m.get.return_value = _make_db()
        tl = TraitLevel(id=uuid4(), trait_level_name="X")
        assert tl.delete() is True

    @patch(f"{MODULE}.TraitLevelModel")
    def test_not_found(self, m):
        m.get.return_value = None
        tl = TraitLevel(id=uuid4(), trait_level_name="X")
        assert tl.delete() is False


class TestTraitLevelRefresh:
    @patch(f"{MODULE}.TraitLevelModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        tl = TraitLevel(id=uid, trait_level_name="X")
        assert tl.refresh() is tl

    @patch(f"{MODULE}.TraitLevelModel")
    def test_not_found(self, m):
        m.get.return_value = None
        tl = TraitLevel(id=uuid4(), trait_level_name="X")
        assert tl.refresh() is tl


class TestTraitLevelGetSetInfo:
    @patch(f"{MODULE}.TraitLevelModel")
    def test_get_info(self, m):
        m.get.return_value = _make_db(trait_level_info={"k": "v"})
        tl = TraitLevel(id=uuid4(), trait_level_name="X")
        assert tl.get_info() == {"k": "v"}

    @patch(f"{MODULE}.TraitLevelModel")
    def test_get_info_empty(self, m):
        m.get.return_value = _make_db(trait_level_info=None)
        tl = TraitLevel(id=uuid4(), trait_level_name="X")
        assert tl.get_info() is None

    @patch(f"{MODULE}.TraitLevelModel")
    def test_set_info(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid)
        tl = TraitLevel(id=uid, trait_level_name="X")
        assert tl.set_info({"new": "v"}) is not None
