"""One dataset per analysis run; re-runs replace their predecessors."""
from unittest.mock import MagicMock, create_autospec

import pytest

from gemini.workers.auth import WorkerSession

from gemini.workers.ml.trait_ingest import (
    TraitIngestError,
    _replace_previous_runs,
    ingest_trait_features,
    run_dataset_base,
    run_dataset_name,
)

SCOPE = {
    "year": "2024",
    "experiment_name": "Cowpea Trial",
    "site_name": "Davis",
    "population_name": "MAGIC",
    "date": "2024-06-01",
    "platform": "DJI",
    "sensor": "RGB",
}


def test_names_carry_the_experiment_and_scope():
    a = run_dataset_base("EXTRACT_TRAITS", SCOPE)
    b = run_dataset_base("EXTRACT_TRAITS", {**SCOPE, "experiment_name": "Bean Trial"})
    assert a == "EXTRACT_TRAITS · Cowpea Trial · 2024/Davis/MAGIC · 2024-06-01 DJI/RGB"
    assert a != b  # the old "{source} {date} {platform}/{sensor}" collided here
    assert run_dataset_name("EXTRACT_TRAITS", SCOPE, "0123456789abcdef") == a + " · 01234567"
    assert run_dataset_base("LOCATE_PLANTS", SCOPE, "weeds").endswith(" · weeds")


def test_long_scopes_fit_the_column():
    long = {**SCOPE, "experiment_name": "E" * 200, "population_name": "P" * 100}
    name = run_dataset_name("EXTRACT_TRAITS", long, "abcdef1234")
    assert len(name) <= 255
    # Still deterministic, so a re-run finds it.
    assert name == run_dataset_name("EXTRACT_TRAITS", long, "abcdef1234")


def test_replace_deletes_only_this_analysis_earlier_runs():
    base = run_dataset_base("LOCATE_PLANTS", SCOPE, "weeds")
    keep = f"{base} · newrun01"
    # Autospec: a method WorkerSession lacks (it once had no .delete) fails
    # here instead of only in production.
    http = create_autospec(WorkerSession, instance=True)
    http.get.return_value.ok = True
    http.get.return_value.json.return_value = [
        {"id": "1", "dataset_name": f"{base} · oldrun01"},  # earlier run → delete
        {"id": "2", "dataset_name": keep},  # this run → keep
        {"id": "3", "dataset_name": f"{run_dataset_base('LOCATE_PLANTS', SCOPE, 'weeds2')} · x"},
        {"id": "4", "dataset_name": "LOCATE_PLANTS 2024-06-01 DJI/RGB"},  # legacy, shared
        {"id": "5", "dataset_name": f"{run_dataset_base('EXTRACT_TRAITS', SCOPE)} · y"},
    ]
    http.delete.return_value.ok = True
    removed = _replace_previous_runs(
        http, experiment_name="Cowpea Trial", base=base, keep=keep
    )
    assert removed == [f"{base} · oldrun01"]
    http.delete.assert_called_once_with("/api/datasets/id/1")
    assert http.get.call_args.kwargs["params"] == {"experiment_name": "Cowpea Trial"}


def test_ingest_with_run_id_replaces_then_creates_its_own_dataset():
    http = MagicMock()
    http.get.return_value.ok = True
    http.get.return_value.json.return_value = []
    http.post.return_value.ok = True
    http.post.return_value.json.return_value = {"id": "t1", "inserted_count": 1}
    path = "Processed/2024/Cowpea Trial/Davis/MAGIC/2024-06-01/DJI/RGB/traits/v1-b1-traits.geojson"
    feats = [{"type": "Feature", "properties": {"plot": 1, "row": 1, "col": 1, "VF": 0.5}}]
    ingest_trait_features(
        http,
        output_path=path,
        geojson={"type": "FeatureCollection", "features": feats},
        trait_columns=[("VF", "")],
        source="EXTRACT_TRAITS",
        run_id="deadbeefcafe",
    )
    # The replacement lookup happened, scoped to this experiment.
    http.get.assert_any_call("/api/datasets", params={"experiment_name": "Cowpea Trial"})
    created = [c for c in http.post.call_args_list if c.args[0] == "/api/datasets"][0]
    body = created.kwargs["json"]
    assert body["dataset_name"].endswith(" · deadbeef")
    assert body["dataset_info"] == {"source": "EXTRACT_TRAITS", "job_id": "deadbeefcafe"}


PATH = "Processed/2024/Cowpea Trial/Davis/MAGIC/2024-06-01/DJI/RGB/traits/v1-b1-traits.geojson"
FEATS = [{"type": "Feature", "properties": {"plot": 1, "row": 1, "col": 1, "VF": 0.5}}]
BASE = run_dataset_base("EXTRACT_TRAITS", SCOPE)


def _session(bulk_ok: bool):
    """A WorkerSession whose bulk insert succeeds or fails; one earlier run exists."""
    http = create_autospec(WorkerSession, instance=True)

    def get(path, params=None):
        r = MagicMock(ok=True)
        if path == "/api/datasets":
            r.json.return_value = [
                {"id": "old", "dataset_name": f"{BASE} · oldrun01"},
                {"id": "new", "dataset_name": f"{BASE} · deadbeef"},
            ]
        else:  # /api/traits
            r.json.return_value = [{"id": "t1", "trait_name": "VF"}]
        return r

    def post(path, json=None):
        r = MagicMock(ok=True, status_code=200)
        if path.endswith("/records/bulk") and not bulk_ok:
            r.ok, r.status_code, r.text = False, 500, "boom"
        r.json.return_value = {"id": "t1", "inserted_count": 1}
        return r

    http.get.side_effect = get
    http.post.side_effect = post
    http.delete.return_value.ok = True
    return http


def test_previous_run_is_deleted_only_after_the_new_records_land():
    http = _session(bulk_ok=True)
    calls = []
    http.post.side_effect = (lambda f: lambda *a, **k: (calls.append(("post", a[0])), f(*a, **k))[1])(http.post.side_effect)
    http.delete.side_effect = lambda path: (calls.append(("delete", path)), MagicMock(ok=True))[1]
    counts = ingest_trait_features(
        http, output_path=PATH, geojson={"type": "FeatureCollection", "features": FEATS},
        trait_columns=[("VF", "")], source="EXTRACT_TRAITS", run_id="deadbeefcafe",
    )
    assert counts == {"VF": 1}
    bulk = calls.index(("post", "/api/traits/id/t1/records/bulk"))
    assert calls.index(("delete", "/api/datasets/id/old")) > bulk
    assert ("delete", "/api/datasets/id/new") not in calls


def test_failed_insert_raises_keeps_earlier_run_and_drops_its_own():
    http = _session(bulk_ok=False)
    with pytest.raises(TraitIngestError, match="Earlier results were kept"):
        ingest_trait_features(
            http, output_path=PATH, geojson={"type": "FeatureCollection", "features": FEATS},
            trait_columns=[("VF", "")], source="EXTRACT_TRAITS", run_id="deadbeefcafe",
        )
    http.delete.assert_called_once_with("/api/datasets/id/new")
