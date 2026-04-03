"""Tests for gemini.api.site module - Site class.

This is the TEMPLATE for all entity tests. All other entity tests follow this pattern.
"""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from gemini.api.site import Site


SITE_MODULE = "gemini.api.site"


def _make_site_db_instance(**overrides):
    """Create a mock SiteModel DB instance."""
    defaults = {
        "id": uuid4(),
        "site_name": "Test Site",
        "site_city": "Davis",
        "site_state": "CA",
        "site_country": "US",
        "site_info": {"key": "value"},
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.__dict__.update(defaults)
    return mock


class TestSiteExists:
    """Tests for Site.exists()."""

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_exists_returns_true(self, mock_model):
        mock_model.exists.return_value = True
        assert Site.exists(site_name="Test Site") is True
        mock_model.exists.assert_called_once_with(site_name="Test Site")

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_exists_returns_false(self, mock_model):
        mock_model.exists.return_value = False
        assert Site.exists(site_name="Missing") is False

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_exists_returns_false_on_exception(self, mock_model):
        mock_model.exists.side_effect = Exception("DB error")
        assert Site.exists(site_name="Test Site") is False


class TestSiteCreate:
    """Tests for Site.create()."""

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_create_success(self, mock_model):
        db_inst = _make_site_db_instance()
        mock_model.get_or_create.return_value = db_inst
        site = Site.create(site_name="Test Site", site_city="Davis")
        assert site is not None
        assert site.site_name == "Test Site"
        mock_model.get_or_create.assert_called_once()

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_create_with_experiment(self, mock_model):
        db_inst = _make_site_db_instance()
        mock_model.get_or_create.return_value = db_inst
        with patch.object(Site, "associate_experiment", return_value=MagicMock()) as mock_assoc:
            site = Site.create(site_name="Test Site", experiment_name="Exp1")
            assert site is not None
            mock_assoc.assert_called_once_with("Exp1")

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_create_returns_none_on_exception(self, mock_model):
        mock_model.get_or_create.side_effect = Exception("DB error")
        result = Site.create(site_name="Test Site")
        assert result is None


class TestSiteGet:
    """Tests for Site.get()."""

    @patch(f"{SITE_MODULE}.ExperimentSitesViewModel")
    def test_get_found(self, mock_view):
        db_inst = _make_site_db_instance()
        mock_view.get_by_parameters.return_value = db_inst
        site = Site.get(site_name="Test Site")
        assert site is not None
        assert site.site_name == "Test Site"

    @patch(f"{SITE_MODULE}.ExperimentSitesViewModel")
    def test_get_not_found(self, mock_view):
        mock_view.get_by_parameters.return_value = None
        result = Site.get(site_name="Missing")
        assert result is None

    @patch(f"{SITE_MODULE}.ExperimentSitesViewModel")
    def test_get_with_experiment(self, mock_view):
        db_inst = _make_site_db_instance()
        mock_view.get_by_parameters.return_value = db_inst
        site = Site.get(site_name="Test Site", experiment_name="Exp1")
        mock_view.get_by_parameters.assert_called_once_with(
            site_name="Test Site", experiment_name="Exp1"
        )

    @patch(f"{SITE_MODULE}.ExperimentSitesViewModel")
    def test_get_returns_none_on_exception(self, mock_view):
        mock_view.get_by_parameters.side_effect = Exception("DB error")
        result = Site.get(site_name="Test Site")
        assert result is None


class TestSiteGetById:
    """Tests for Site.get_by_id()."""

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_get_by_id_found(self, mock_model):
        uid = uuid4()
        db_inst = _make_site_db_instance(id=uid)
        mock_model.get.return_value = db_inst
        site = Site.get_by_id(uid)
        assert site is not None
        assert site.id == uid

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_get_by_id_not_found(self, mock_model):
        mock_model.get.return_value = None
        result = Site.get_by_id(uuid4())
        assert result is None

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_get_by_id_exception(self, mock_model):
        mock_model.get.side_effect = Exception("DB error")
        result = Site.get_by_id(uuid4())
        assert result is None


class TestSiteGetAll:
    """Tests for Site.get_all()."""

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_get_all_returns_list(self, mock_model):
        mock_model.all.return_value = [_make_site_db_instance(), _make_site_db_instance(site_name="Site2")]
        sites = Site.get_all()
        assert sites is not None
        assert len(sites) == 2

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_get_all_empty(self, mock_model):
        mock_model.all.return_value = []
        result = Site.get_all()
        assert result is None

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_get_all_none(self, mock_model):
        mock_model.all.return_value = None
        result = Site.get_all()
        assert result is None

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_get_all_exception(self, mock_model):
        mock_model.all.side_effect = Exception("DB error")
        result = Site.get_all()
        assert result is None


class TestSiteSearch:
    """Tests for Site.search()."""

    @patch(f"{SITE_MODULE}.ExperimentSitesViewModel")
    def test_search_returns_results(self, mock_view):
        mock_view.search.return_value = [_make_site_db_instance()]
        results = Site.search(site_name="Test Site")
        assert results is not None
        assert len(results) == 1

    @patch(f"{SITE_MODULE}.ExperimentSitesViewModel")
    def test_search_no_results(self, mock_view):
        mock_view.search.return_value = []
        result = Site.search(site_name="Missing")
        assert result is None

    def test_search_no_params(self):
        result = Site.search()
        assert result is None

    @patch(f"{SITE_MODULE}.ExperimentSitesViewModel")
    def test_search_exception(self, mock_view):
        mock_view.search.side_effect = Exception("DB error")
        result = Site.search(site_name="Test Site")
        assert result is None


class TestSiteUpdate:
    """Tests for Site.update() instance method."""

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_update_success(self, mock_model):
        uid = uuid4()
        db_inst = _make_site_db_instance(id=uid)
        mock_model.get.return_value = db_inst
        updated_db = _make_site_db_instance(id=uid, site_city="New City")
        mock_model.update.return_value = updated_db

        site = Site(id=uid, site_name="Test Site", site_city="Davis")
        result = site.update(site_city="New City")
        assert result is not None

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_update_no_params(self, mock_model):
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.update()
        assert result is None

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_update_not_found(self, mock_model):
        mock_model.get.return_value = None
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.update(site_city="New City")
        assert result is None

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_update_exception(self, mock_model):
        mock_model.get.side_effect = Exception("DB error")
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.update(site_city="New City")
        assert result is None


class TestSiteDelete:
    """Tests for Site.delete() instance method."""

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_delete_success(self, mock_model):
        uid = uuid4()
        db_inst = _make_site_db_instance(id=uid)
        mock_model.get.return_value = db_inst
        site = Site(id=uid, site_name="Test Site")
        result = site.delete()
        assert result is True
        mock_model.delete.assert_called_once_with(db_inst)

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_delete_not_found(self, mock_model):
        mock_model.get.return_value = None
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.delete()
        assert result is False

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_delete_exception(self, mock_model):
        mock_model.get.side_effect = Exception("DB error")
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.delete()
        assert result is False


class TestSiteRefresh:
    """Tests for Site.refresh() instance method."""

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_refresh_success(self, mock_model):
        uid = uuid4()
        db_inst = _make_site_db_instance(id=uid, site_city="Updated City")
        mock_model.get.return_value = db_inst
        site = Site(id=uid, site_name="Test Site", site_city="Old City")
        result = site.refresh()
        assert result is site
        assert site.site_city == "Updated City"

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_refresh_not_found(self, mock_model):
        mock_model.get.return_value = None
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.refresh()
        assert result is site

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_refresh_exception(self, mock_model):
        mock_model.get.side_effect = Exception("DB error")
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.refresh()
        assert result is None


class TestSiteGetInfo:
    """Tests for Site.get_info()."""

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_get_info_success(self, mock_model):
        uid = uuid4()
        db_inst = _make_site_db_instance(id=uid, site_info={"key": "value"})
        mock_model.get.return_value = db_inst
        site = Site(id=uid, site_name="Test Site")
        result = site.get_info()
        assert result == {"key": "value"}

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_get_info_not_found(self, mock_model):
        mock_model.get.return_value = None
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.get_info()
        assert result is None

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_get_info_empty(self, mock_model):
        db_inst = _make_site_db_instance(site_info=None)
        mock_model.get.return_value = db_inst
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.get_info()
        assert result is None

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_get_info_exception(self, mock_model):
        mock_model.get.side_effect = Exception("DB error")
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.get_info()
        assert result is None


class TestSiteSetInfo:
    """Tests for Site.set_info()."""

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_set_info_success(self, mock_model):
        uid = uuid4()
        db_inst = _make_site_db_instance(id=uid)
        mock_model.get.return_value = db_inst
        updated_db = _make_site_db_instance(id=uid, site_info={"new": "info"})
        mock_model.update.return_value = updated_db
        site = Site(id=uid, site_name="Test Site")
        result = site.set_info({"new": "info"})
        assert result is not None

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_set_info_not_found(self, mock_model):
        mock_model.get.return_value = None
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.set_info({"new": "info"})
        assert result is None

    @patch(f"{SITE_MODULE}.SiteModel")
    def test_set_info_exception(self, mock_model):
        mock_model.get.side_effect = Exception("DB error")
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.set_info({"new": "info"})
        assert result is None


class TestSiteAssociations:
    """Tests for Site association methods."""

    @patch(f"{SITE_MODULE}.ExperimentSitesViewModel")
    def test_get_associated_experiments_found(self, mock_view):
        mock_view.search.return_value = [_make_site_db_instance()]
        site = Site(id=uuid4(), site_name="Test Site")
        with patch("gemini.api.site.Experiment", create=True) as mock_exp_cls:
            # The import inside the method uses Experiment.model_validate
            from unittest.mock import ANY
            result = site.get_associated_experiments()
            mock_view.search.assert_called_once_with(site_id=site.id)

    @patch(f"{SITE_MODULE}.ExperimentSitesViewModel")
    def test_get_associated_experiments_none(self, mock_view):
        mock_view.search.return_value = []
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.get_associated_experiments()
        assert result is None

    @patch(f"{SITE_MODULE}.ExperimentSitesViewModel")
    def test_get_associated_experiments_exception(self, mock_view):
        mock_view.search.side_effect = Exception("DB error")
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.get_associated_experiments()
        assert result is None

    @patch(f"{SITE_MODULE}.ExperimentSiteModel")
    def test_associate_experiment_success(self, mock_assoc_model):
        mock_assoc_model.get_by_parameters.return_value = None
        mock_assoc_model.get_or_create.return_value = MagicMock()
        site = Site(id=uuid4(), site_name="Test Site")
        with patch("gemini.api.experiment.Experiment") as mock_exp_cls:
            mock_exp = MagicMock()
            mock_exp.id = uuid4()
            with patch("gemini.api.site.Experiment", create=True) as mock_inner:
                mock_inner.get.return_value = mock_exp
                with patch.object(site, "refresh"):
                    result = site.associate_experiment("Exp1")

    @patch(f"{SITE_MODULE}.ExperimentSiteModel")
    def test_associate_experiment_not_found(self, mock_assoc_model):
        site = Site(id=uuid4(), site_name="Test Site")
        with patch("gemini.api.site.Experiment", create=True) as mock_inner:
            mock_inner.get.return_value = None
            result = site.associate_experiment("Missing Exp")
            assert result is None

    @patch(f"{SITE_MODULE}.ExperimentSiteModel")
    def test_unassociate_experiment_success(self, mock_assoc_model):
        mock_assoc_model.get_by_parameters.return_value = MagicMock()
        mock_assoc_model.delete.return_value = True
        site = Site(id=uuid4(), site_name="Test Site")
        with patch("gemini.api.experiment.Experiment") as mock_inner:
            mock_exp = MagicMock()
            mock_exp.id = uuid4()
            mock_inner.get.return_value = mock_exp
            with patch.object(site, "refresh"):
                result = site.unassociate_experiment("Exp1")
                assert result is mock_exp

    @patch(f"{SITE_MODULE}.ExperimentSiteModel")
    def test_unassociate_experiment_no_association(self, mock_assoc_model):
        mock_assoc_model.get_by_parameters.return_value = None
        site = Site(id=uuid4(), site_name="Test Site")
        with patch("gemini.api.site.Experiment", create=True) as mock_inner:
            mock_inner.get.return_value = MagicMock()
            result = site.unassociate_experiment("Exp1")
            assert result is None

    @patch(f"{SITE_MODULE}.ExperimentSiteModel")
    def test_belongs_to_experiment_true(self, mock_assoc_model):
        mock_assoc_model.exists.return_value = True
        site = Site(id=uuid4(), site_name="Test Site")
        with patch("gemini.api.experiment.Experiment") as mock_inner:
            mock_exp = MagicMock()
            mock_exp.id = uuid4()
            mock_inner.get.return_value = mock_exp
            result = site.belongs_to_experiment("Exp1")
            assert result is True

    @patch(f"{SITE_MODULE}.ExperimentSiteModel")
    def test_belongs_to_experiment_false(self, mock_assoc_model):
        mock_assoc_model.exists.return_value = False
        site = Site(id=uuid4(), site_name="Test Site")
        with patch("gemini.api.site.Experiment", create=True) as mock_inner:
            mock_exp = MagicMock()
            mock_exp.id = uuid4()
            mock_inner.get.return_value = mock_exp
            result = site.belongs_to_experiment("Exp1")
            assert result is False

    @patch(f"{SITE_MODULE}.PlotViewModel")
    def test_get_associated_plots_found(self, mock_view):
        mock_view.search.return_value = [MagicMock(
            id=uuid4(), plot_number=1, plot_row_number=1, plot_column_number=1
        )]
        site = Site(id=uuid4(), site_name="Test Site")
        with patch("gemini.api.site.Plot", create=True):
            result = site.get_associated_plots()
            mock_view.search.assert_called_once_with(site_id=site.id)

    @patch(f"{SITE_MODULE}.PlotViewModel")
    def test_get_associated_plots_none(self, mock_view):
        mock_view.search.return_value = []
        site = Site(id=uuid4(), site_name="Test Site")
        result = site.get_associated_plots()
        assert result is None


class TestSiteStringRepresentation:
    """Tests for __str__ and __repr__."""

    def test_str(self):
        uid = uuid4()
        site = Site(id=uid, site_name="Test Site")
        assert "Test Site" in str(site)

    def test_repr(self):
        uid = uuid4()
        site = Site(id=uid, site_name="Test Site")
        assert "Test Site" in repr(site)
