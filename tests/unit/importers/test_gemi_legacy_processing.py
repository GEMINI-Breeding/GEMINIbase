"""Old-GEMI importer, tiers 2–3: conversions and the dry-run counts.

The REST side (versions, traits, process documents, archive) is exercised
end to end by frontend/tests/e2e/legacy-import.spec.ts on the fixture old
install (frontend/tests/fixtures/legacy).
"""
import json
import sqlite3
import uuid
from pathlib import Path

import pytest

from gemini.importers.gemi_legacy.processing import (
    as_int,
    canonical_boundaries,
    plan_processing,
    selections_from_csv,
    ws_tag,
)
from gemini.importers.gemi_legacy.reader import LegacyDatabase

FIXTURES = Path(__file__).parents[2] / "fixtures" / "gemi_legacy"


@pytest.mark.parametrize("value, expected", [
    ("3", 3), ("3.0", 3), (3.0, 3), (4, 4), ("3.5", None), ("", None), (None, None), ("x", None),
])
def test_as_int(value, expected):
    assert as_int(value) == expected


def test_boundary_identity_uses_the_old_apps_alternatives():
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": None,
         "properties": {"Plot": "7", "Tier": "2.0", "Bed": 3, "Label": "CB27", "extra": "x"}},
        {"type": "Feature", "geometry": None,
         "properties": {"plot_id": 8, "row": 1, "column": "4", "accession": "IT97"}},
        {"type": "Feature", "geometry": None, "properties": {"name": "hand-drawn"}},
    ]}
    props = [f["properties"] for f in canonical_boundaries(fc)["features"]]
    assert {k: props[0][k] for k in ("plot", "row", "col", "accession", "extra", "Plot")} == {
        "plot": 7, "row": 2, "col": 3, "accession": "CB27", "extra": "x", "Plot": "7"}
    assert (props[1]["plot"], props[1]["row"], props[1]["col"], props[1]["accession"]) == (8, 1, 4, "IT97")
    assert "plot" not in props[2]  # nothing to identify it by: left as it was


def test_plot_marking_csv_becomes_selections():
    text = ("plot_id,start_image,end_image,direction,start_lat,start_lon,end_lat,end_lon\n"
            "1,rgb-1.jpg,rgb-2.jpg,South,38.5,-121.7,38.4,\n"
            "B7,rgb-3.jpg,rgb-4.jpg,North,,,,\n")
    a, b = selections_from_csv(text)
    assert a == {"plot_id": 1, "start_image": "rgb-1.jpg", "end_image": "rgb-2.jpg", "direction": "South",
                 "start_lat": 38.5, "start_lon": -121.7, "end_lat": 38.4, "end_lon": None}
    assert b["plot_id"] == "B7" and b["start_lat"] is None


def test_workspace_tag_is_filename_safe_and_distinct():
    a = ws_tag("Drone 2024 / Davis!", "ab12cd34-0000-0000-0000-000000000000")
    b = ws_tag("Drone 2024 / Davis!", "ff00ee11-0000-0000-0000-000000000000")
    assert a == "Drone2024Dav" + "ab12" and a != b
    assert ws_tag("!!!", "12345678-0000-0000-0000-000000000000") == "ws1234"


def make_db(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript((FIXTURES / "schema-v0.0.5.sql").read_text())
    ws, pipe, gone = uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex
    conn.execute("INSERT INTO workspace (name, description, id, owner_id, created_at) VALUES (?,?,?,?,?)",
                 ("WS", "", ws, uuid.uuid4().hex, "2025-01-01"))
    conn.execute("INSERT INTO pipeline (name, type, config, id, workspace_id, created_at) VALUES (?,?,?,?,?,?)",
                 ("P", "aerial", "{}", pipe, ws, "2025-01-01"))
    outputs = {
        "orthomosaics": [{"version": 1, "rgb": "a.tif"}, {"version": 2, "rgb": "b.tif"}],
        "plot_boundaries": [{"version": 1, "geojson_path": "b1.geojson"}],
    }
    legacy_flat = {"orthomosaic": "old.tif", "dem": "old-dem.tif"}
    for run_id, pipeline, out in ((uuid.uuid4().hex, pipe, outputs), (uuid.uuid4().hex, pipe, legacy_flat),
                                  (uuid.uuid4().hex, gone, outputs)):
        conn.execute(
            "INSERT INTO pipelinerun (pipeline_id, date, experiment, location, population, platform, sensor, "
            "status, steps_completed, outputs, id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (pipeline, "2025-06-10", "E", "L", "P", "Drone", "RGB", "completed", "{}", json.dumps(out),
             run_id, "2025-06-10"))
    conn.commit()
    conn.close()
    return path


def test_dry_run_counts_and_orphans(tmp_path):
    data = tmp_path / "data"
    (data / "Processed/WS/2025/E").mkdir(parents=True)
    (data / "Processed/WS/2025/E/Traits-WGS84.geojson").write_text("{}")
    (data / "Intermediate/WS/2025/E").mkdir(parents=True)
    (data / "Intermediate/WS/2025/E/plot_borders.csv").write_text("x\n")
    (data / "Raw/2025/E").mkdir(parents=True)
    (data / "Raw/2025/E/not-archived.jpg").write_text("x")
    with LegacyDatabase(make_db(tmp_path / "gemi.db")) as db:
        s = plan_processing(db, data).summary()
    assert (s["workspaces"], s["pipelines"], s["runs"]) == (1, 1, 2)
    # Two versioned orthos + the pre-versioning flat key as one.
    assert s["ortho_versions"] == 3 and s["boundary_versions"] == 1
    assert s["archive_files"] == 2  # Intermediate/ + Processed/, not Raw/
    assert s["notes"] == ["1 run(s) of deleted pipelines are only in the archive copy"]
