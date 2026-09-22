"""Rules for turning LOCATE_PLANTS batch results into trait records.

The one that matters most: a plot that was inferred and had no detections
records 0 (that is a measurement), while a plot that errored or had no
image records NOTHING — writing 0 there would claim "we looked and found
nothing" for a plot nobody looked at.
"""
from unittest.mock import patch

from gemini.workers.ml.trait_ingest import _features_to_records
from gemini.workers.ml.worker import MlWorker


def _feat(plot, row, col, **extra):
    return {
        "type": "Feature",
        "properties": {"plot": plot, "row": row, "col": col, **extra},
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
    }


BOUNDS = {"type": "FeatureCollection", "features": [_feat(1, 1, 1), _feat(2, 1, 2), _feat(3, 1, 3)]}


def _run(by_plot, classes):
    w = MlWorker.__new__(MlWorker)
    w._http = object()
    with patch(
        "gemini.workers.ml.trait_ingest.ingest_trait_features",
        side_effect=lambda http, **kw: kw,
    ) as ingest:
        kw = MlWorker._ingest_detection_counts(
            w,
            boundaries=BOUNDS,
            by_plot=by_plot,
            classes=classes,
            label="Stand",
            output_path="Processed/2024/E/S/P/2024-06-01/Drone/RGB/PlotImages/inference/x.json",
        )
    return ingest, kw


def _props_by_plot(kw):
    return {f["properties"]["plot"]: f["properties"] for f in kw["geojson"]["features"]}


def test_inferred_with_no_detections_records_zero():
    by_plot = {
        "1": {"count": 3, "counts_by_class": {"plant": 3}},
        "2": {"count": 0, "counts_by_class": {}},
    }
    _, kw = _run(by_plot, ["plant"])
    props = _props_by_plot(kw)
    assert props[2]["detections (Stand)"] == 0
    assert props[2]["plant count (Stand)"] == 0


def test_errored_or_missing_plot_writes_no_record():
    # Plot 3 isn't in by_plot at all — it errored, or had no image.
    by_plot = {"1": {"count": 1, "counts_by_class": {"plant": 1}}}
    _, kw = _run(by_plot, ["plant"])
    assert set(_props_by_plot(kw)) == {1}


def test_per_class_counts_and_total():
    by_plot = {"1": {"count": 5, "counts_by_class": {"plant": 3, "weed": 2}}}
    _, kw = _run(by_plot, ["plant", "weed"])
    p = _props_by_plot(kw)[1]
    assert p["detections (Stand)"] == 5
    assert p["plant count (Stand)"] == 3
    assert p["weed count (Stand)"] == 2
    names = [name for name, _ in kw["trait_columns"]]
    assert names == ["detections (Stand)", "plant count (Stand)", "weed count (Stand)"]
    assert kw["source"] == "LOCATE_PLANTS"


def test_class_absent_from_one_plot_is_zero_not_missing():
    by_plot = {
        "1": {"count": 2, "counts_by_class": {"plant": 2}},
        "2": {"count": 1, "counts_by_class": {"weed": 1}},
    }
    _, kw = _run(by_plot, ["plant", "weed"])
    props = _props_by_plot(kw)
    assert props[1]["weed count (Stand)"] == 0
    assert props[2]["plant count (Stand)"] == 0


def test_nothing_to_ingest_skips_the_call():
    ingest, kw = _run({}, [])
    assert kw == {}
    ingest.assert_not_called()


def test_features_to_records_stamps_the_source():
    recs = _features_to_records(
        [_feat(4, 2, 3, **{"detections (Stand)": 7})],
        "detections (Stand)",
        source="LOCATE_PLANTS",
    )
    assert recs == [
        {
            "plot_number": 4,
            "plot_row_number": 2,
            "plot_column_number": 3,
            "trait_value": 7.0,
            "accession_name": None,
            "record_info": {"source": "LOCATE_PLANTS"},
        }
    ]


# ── Self-hosted inference server URL ─────────────────────────────────────
from gemini.workers.ml.inference_utils import (  # noqa: E402
    CLOUD_API_URL,
    resolve_inference_api_url,
)


def test_empty_url_means_roboflow_cloud():
    assert resolve_inference_api_url(None) == CLOUD_API_URL
    assert resolve_inference_api_url("") == CLOUD_API_URL
    assert resolve_inference_api_url("   ") == CLOUD_API_URL


def test_localhost_is_rewritten_to_reach_the_host_from_the_container():
    # The form's default. Inside the worker container `localhost` is the
    # container itself, so the literal URL would always be refused.
    assert (
        resolve_inference_api_url("http://localhost:9002")
        == "http://host.docker.internal:9002"
    )
    assert (
        resolve_inference_api_url("http://127.0.0.1:9002/")
        == "http://host.docker.internal:9002"
    )


def test_a_real_hostname_is_left_alone():
    assert (
        resolve_inference_api_url("http://gpu-box.lab:9001")
        == "http://gpu-box.lab:9001"
    )
