"""Matching stitched ground plots to boundary polygons."""
from gemini.workers.stitch import associate


def square(x0, y0, size=1.0, **props):
    ring = [[x0, y0], [x0 + size, y0], [x0 + size, y0 + size], [x0, y0 + size], [x0, y0]]
    return {"type": "Feature", "properties": props,
            "geometry": {"type": "Polygon", "coordinates": [ring]}}


FC = {"type": "FeatureCollection", "features": [
    square(0, 0, plot=1, row=1, col=1, accession="IT97K"),
    square(1, 0, plot=2, row=1, col=2),
    square(-1, -1, size=4, role="outer"),  # a block outline, not a plot
]}


def test_block_outlines_are_not_plots():
    assert [f["properties"]["plot"] for f in associate.plot_polygons(FC)] == [1, 2]


def test_centres_match_the_containing_polygon():
    got = associate.match(
        {"1": (0.5, 0.5), "2": (1.5, 0.2), "3": (5, 5)},
        associate.plot_polygons(FC),
    )
    assert got["1"]["accession"] == "IT97K"
    assert got["2"]["plot"] == 2
    assert got["3"] is None


def test_holes_and_multipolygons():
    donut = {"type": "Polygon", "coordinates": [
        [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]],
        [[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]],
    ]}
    assert associate.contains(donut, (0.5, 0.5))
    assert not associate.contains(donut, (2, 2))
    multi = {"type": "MultiPolygon", "coordinates": [
        [[[0, 0], [1, 0], [1, 1], [0, 0]]],
        [[[5, 5], [6, 5], [6, 6], [5, 5]]],
    ]}
    assert associate.contains(multi, (5.8, 5.2))


def test_plot_image_name_matches_the_aerial_split():
    assert associate.plot_image_name({"plot": 7, "accession": "IT 97/K"}, "3") == (
        "plot_7_accession_IT_97_K.png"
    )
    assert associate.plot_image_name({}, "3") == "plot_3_accession_unknown.png"


def test_plots_marked_from_drone_boundaries_keep_their_plot():
    from gemini.workers.stitch.associate import by_label, marked_plots

    manifest = {"plots": {
        "1": {"boundary": {"label": "101", "properties": {"plot": "101"}}},
        "2": {"frames": 30},
        "3": {"boundary": {"label": ""}},
    }}
    assert marked_plots(manifest) == {"1": "101"}
    assert marked_plots({}) == {}
    feats = [{"properties": {"plot": "101"}, "geometry": {}},
             {"properties": {"plot": "102"}, "geometry": {}},
             {"properties": {"plot": "101", "dup": True}, "geometry": {}}]
    lab = by_label(feats)
    assert set(lab) == {"101", "102"} and "dup" not in lab["101"]["properties"]
