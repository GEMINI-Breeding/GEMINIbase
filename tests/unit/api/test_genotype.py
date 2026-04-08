"""Unit tests for the Genotype API class."""

from unittest.mock import patch, MagicMock
from uuid import uuid4
from gemini.api.genotype import Genotype

MODULE = "gemini.api.genotype"


def _make_db(**overrides):
    defaults = {
        "id": uuid4(),
        "genotype_name": "Cowpea_MAGIC_GBS",
        "genotype_info": {"platform": "GBS"},
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestGenotypeExists:
    @patch(f"{MODULE}.GenotypeModel")
    def test_exists_true(self, m):
        m.exists.return_value = True
        assert Genotype.exists(genotype_name="Cowpea_MAGIC_GBS") is True

    @patch(f"{MODULE}.GenotypeModel")
    def test_exists_false(self, m):
        m.exists.return_value = False
        assert Genotype.exists(genotype_name="nonexistent") is False

    @patch(f"{MODULE}.GenotypeModel")
    def test_exists_exception(self, m):
        m.exists.side_effect = Exception("DB error")
        assert Genotype.exists(genotype_name="test") is False


class TestGenotypeCreate:
    @patch(f"{MODULE}.GenotypeModel")
    def test_create_success(self, m):
        m.get_or_create.return_value = _make_db()
        result = Genotype.create(genotype_name="Cowpea_MAGIC_GBS")
        assert result is not None
        assert result.genotype_name == "Cowpea_MAGIC_GBS"

    @patch(f"{MODULE}.GenotypeModel")
    def test_create_exception(self, m):
        m.get_or_create.side_effect = Exception("DB error")
        result = Genotype.create(genotype_name="test")
        assert result is None

    @patch(f"{MODULE}.GenotypeModel")
    def test_create_with_experiment(self, m):
        m.get_or_create.return_value = _make_db()
        with patch.object(Genotype, "associate_experiment", return_value=MagicMock()):
            result = Genotype.create(genotype_name="test", experiment_name="Exp1")
            assert result is not None


class TestGenotypeGet:
    @patch(f"{MODULE}.GenotypeModel")
    def test_get_success(self, m):
        m.get_by_parameters.return_value = _make_db()
        result = Genotype.get(genotype_name="Cowpea_MAGIC_GBS")
        assert result is not None

    @patch(f"{MODULE}.GenotypeModel")
    def test_get_not_found(self, m):
        m.get_by_parameters.return_value = None
        result = Genotype.get(genotype_name="nonexistent")
        assert result is None

    @patch(f"{MODULE}.ExperimentGenotypesViewModel")
    def test_get_with_experiment(self, m):
        m.get_by_parameters.return_value = _make_db()
        result = Genotype.get(genotype_name="test", experiment_name="Exp1")
        assert result is not None


class TestGenotypeGetById:
    @patch(f"{MODULE}.GenotypeModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        result = Genotype.get_by_id(uid)
        assert result is not None

    @patch(f"{MODULE}.GenotypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        assert Genotype.get_by_id(uuid4()) is None


class TestGenotypeGetAll:
    @patch(f"{MODULE}.GenotypeModel")
    def test_success(self, m):
        m.all.return_value = [_make_db(), _make_db()]
        result = Genotype.get_all()
        assert len(result) == 2

    @patch(f"{MODULE}.GenotypeModel")
    def test_empty(self, m):
        m.all.return_value = []
        assert Genotype.get_all() is None


class TestGenotypeSearch:
    @patch(f"{MODULE}.ExperimentGenotypesViewModel")
    def test_success(self, m):
        m.search.return_value = [_make_db()]
        result = Genotype.search(genotype_name="test")
        assert result is not None
        assert len(result) == 1

    def test_no_params(self):
        assert Genotype.search() is None


class TestGenotypeUpdate:
    @patch(f"{MODULE}.GenotypeModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.update.return_value = _make_db(id=uid, genotype_name="Updated")
        g = Genotype(genotype_name="test", id=uid)
        result = g.update(genotype_name="Updated")
        assert result is not None

    @patch(f"{MODULE}.GenotypeModel")
    def test_no_params(self, m):
        g = Genotype(genotype_name="test", id=uuid4())
        assert g.update() is None


class TestGenotypeDelete:
    @patch(f"{MODULE}.GenotypeModel")
    def test_success(self, m):
        uid = uuid4()
        m.get.return_value = _make_db(id=uid)
        m.delete.return_value = True
        g = Genotype(genotype_name="test", id=uid)
        assert g.delete() is True

    @patch(f"{MODULE}.GenotypeModel")
    def test_not_found(self, m):
        m.get.return_value = None
        g = Genotype(genotype_name="test", id=uuid4())
        assert g.delete() is False


class TestGenotypeAssociations:
    @patch(f"{MODULE}.ExperimentGenotypeModel")
    @patch(f"{MODULE}.ExperimentGenotypesViewModel")
    @patch("gemini.api.experiment.Experiment")
    def test_get_associated_experiments(self, m_exp_cls, m_view, m_assoc):
        mock_view_row = MagicMock()
        m_view.search.return_value = [mock_view_row]
        m_exp_cls.model_validate.return_value = MagicMock()
        g = Genotype(genotype_name="test", id=uuid4())
        result = g.get_associated_experiments()
        assert result is not None

    @patch(f"{MODULE}.ExperimentGenotypeModel")
    @patch("gemini.api.experiment.Experiment")
    def test_associate_experiment(self, m_exp_cls, m_assoc):
        mock_experiment = MagicMock()
        mock_experiment.id = uuid4()
        m_exp_cls.get.return_value = mock_experiment
        m_assoc.get_by_parameters.return_value = None
        m_assoc.get_or_create.return_value = MagicMock()
        g = Genotype(genotype_name="test", id=uuid4())
        with patch.object(g, "refresh"):
            result = g.associate_experiment("Exp1")
            assert result is not None

    @patch(f"{MODULE}.ExperimentGenotypeModel")
    @patch("gemini.api.experiment.Experiment")
    def test_belongs_to_experiment(self, m_exp_cls, m_assoc):
        mock_experiment = MagicMock()
        mock_experiment.id = uuid4()
        m_exp_cls.get.return_value = mock_experiment
        m_assoc.exists.return_value = True
        g = Genotype(genotype_name="test", id=uuid4())
        assert g.belongs_to_experiment("Exp1") is True
