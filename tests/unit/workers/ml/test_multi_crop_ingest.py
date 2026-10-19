"""An upload holding several crops: each plot's records land in its own population."""
from unittest.mock import MagicMock

from gemini.workers.ml.trait_ingest import ingest_trait_features, plot_population

PATH = "Processed/2024/GEMINI/Davis/Mixed/2024-06-01/DJI/RGB/traits/v1-b1-traits.geojson"


def _feature(plot, crop=None, value=0.5):
    props = {"plot": plot, "row": 1, "col": plot, "VF": value}
    if crop:
        props["crop"] = crop
    return {"type": "Feature", "properties": props}


def test_plot_population_reads_the_design_columns():
    assert plot_population({"crop": "Cowpea"}) == "Cowpea"
    assert plot_population({"Population_exact": " CowpeaMAGIC "}) == "CowpeaMAGIC"
    assert plot_population({"population_name": "A", "crop": "B"}) == "A"
    assert plot_population({"crop": ""}) is None
    assert plot_population({}) is None


def test_records_are_posted_per_population_and_missing_ones_are_made():
    made = []
    posts = []
    http = MagicMock()

    def get(path, params=None):
        r = MagicMock(ok=True)
        if path == "/api/populations":
            r.json.return_value = [{"population_name": "Cowpea"}] if params["population_name"] == "Cowpea" else []
        elif path == "/api/traits":
            r.json.return_value = [{"id": "t1", "trait_name": "VF"}]
        else:
            r.json.return_value = []
        return r

    def post(path, json=None):
        r = MagicMock(ok=True, status_code=200)
        if path == "/api/populations":
            made.append(json["population_name"])
        if path.endswith("/records/bulk"):
            posts.append((json["population_name"], [x["plot_number"] for x in json["records"]]))
            r.json.return_value = {"inserted_count": len(json["records"])}
        else:
            r.json.return_value = {"id": "t1"}
        return r

    http.get.side_effect = get
    http.post.side_effect = post
    feats = [_feature(1, "Cowpea"), _feature(2, "Sorghum"), _feature(3, "Cowpea"), _feature(4)]
    counts = ingest_trait_features(
        http,
        output_path=PATH,
        geojson={"type": "FeatureCollection", "features": feats},
        trait_columns=[("VF", "")],
        source="EXTRACT_TRAITS",
    )
    assert counts == {"VF": 4}
    assert sorted(posts) == [("Cowpea", [1, 3]), ("Mixed", [4]), ("Sorghum", [2])]
    assert made == ["Sorghum"]  # Cowpea already existed; the upload's own is not touched
    # the private key never reaches the API
    for c in http.post.call_args_list:
        for rec in (c.kwargs.get("json") or {}).get("records", []):
            assert "_population" not in rec
