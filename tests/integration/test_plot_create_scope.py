"""Plot.create must not hand back a plot from a different site/season/experiment.

The existing-plot lookup used to drop any scope ID that was None, so an
unresolved or omitted name matched a plot with the same coordinates
anywhere in the experiment (or anywhere at all).

Requires: docker compose -f tests/docker-compose.test.yaml up -d
"""
import pytest

pytestmark = pytest.mark.integration

COORDS = {"plot_number": 1, "plot_row_number": 1, "plot_column_number": 1}


@pytest.fixture
def scope(setup_real_db, monkeypatch):
    from types import SimpleNamespace

    from gemini.api.season import Season
    from gemini.api.site import Site
    from gemini.db.models.experiments import ExperimentModel
    from gemini.db.models.seasons import SeasonModel
    from gemini.db.models.sites import SiteModel

    exp = ExperimentModel.get_or_create(experiment_name="Plot Scope Exp")
    SeasonModel.get_or_create(experiment_id=exp.id, season_name="2024")
    SiteModel.get_or_create(site_name="Davis")
    SiteModel.get_or_create(site_name="Woodland")

    # Season.get/Site.get read views the test schema doesn't create, so
    # resolve names straight from the tables.
    def _found(row):
        return SimpleNamespace(id=row.id) if row else None

    monkeypatch.setattr(Season, "get", classmethod(
        lambda cls, season_name, experiment_name=None: _found(
            SeasonModel.get_by_parameters(season_name=season_name, experiment_id=exp.id)
        )
    ))
    monkeypatch.setattr(Site, "get", classmethod(
        lambda cls, site_name, experiment_name=None: _found(
            SiteModel.get_by_parameters(site_name=site_name)
        )
    ))


def _create(**kwargs):
    from gemini.api.plot import Plot
    return Plot.create(experiment_name="Plot Scope Exp", **COORDS, **kwargs)


def test_unknown_site_name_does_not_return_another_sites_plot(scope):
    davis = _create(season_name="2024", site_name="Davis")
    assert davis is not None

    typo = _create(season_name="2024", site_name="Davsi")
    assert typo is None or str(typo.id) != str(davis.id)


def test_unknown_site_name_is_rejected(scope):
    assert _create(season_name="2024", site_name="Davsi") is None


def test_plot_without_season_is_distinct_from_seasoned_plot(scope):
    seasoned = _create(season_name="2024", site_name="Davis")
    unseasoned = _create(site_name="Davis")
    assert unseasoned is not None
    assert str(unseasoned.id) != str(seasoned.id)


def test_same_scope_returns_existing_plot(scope):
    first = _create(season_name="2024", site_name="Woodland")
    again = _create(season_name="2024", site_name="Woodland")
    assert str(again.id) == str(first.id)
