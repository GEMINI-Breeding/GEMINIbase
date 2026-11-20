"""A ground track's raw frames: a plot's tiles (frames that do not overlap)
add up to its count; other images of a plot (views of the same ground) do not."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("PIL")
from gemini.workers.ml import worker as W  # noqa: E402


def _run(prefix, names, per_image):
    obj = [SimpleNamespace(object_name=prefix + n) for n in names]
    client = MagicMock()
    client.list_objects.return_value = obj
    spec = SimpleNamespace(display_id="m", source="local", task_type="detection")
    me = W.MlWorker.__new__(W.MlWorker)
    me.report_progress = MagicMock()
    me.is_cancelled = MagicMock(return_value=False)

    def predict(_spec, local, _p):
        n = per_image[local.rsplit("_", 1)[-1] if False else next(k for k in per_image if local.endswith(k))]
        return [{"class": "flower", "confidence": 0.9}] * n

    with patch.object(W, "_get_minio_client", return_value=client), \
            patch.object(W, "_resolve_model_spec", return_value=spec), \
            patch.object(W, "_predict", side_effect=predict):
        return me._locate_plants_batch("job", {"images_prefix": prefix})


def test_tiles_of_a_plot_add_up():
    names = ["plot_1_accession_A_tile01.jpg", "plot_1_accession_A_tile02.jpg",
             "plot_1_accession_A_tile03.jpg", "plot_2_accession_B_tile01.jpg"]
    per = {"tile01.jpg": 2, "tile02.jpg": 3, "tile03.jpg": 4}
    r = _run("Processed/x/PlotFrames/tiles/", names, per)
    assert r["counts_by_plot"] == {"1": 9, "2": 2}
    assert r["summed_over_tiles"] == {"1": 3, "2": 1}


def test_crops_of_a_plot_count_once():
    names = ["plot_1_accession_A_frame1_x.jpg", "plot_1_accession_A_frame2_y.jpg"]
    per = {"x.jpg": 5, "y.jpg": 7}
    r = _run("Processed/x/PlotFrames/crops/", names, per)
    assert r["counts_by_plot"] == {"1": 5}
    assert "summed_over_tiles" not in r
