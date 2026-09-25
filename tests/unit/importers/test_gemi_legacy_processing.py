"""Old-GEMI importer, tiers 2–3: conversions and the dry-run counts.

Trait sets and reference data are also run against a fake server here;
the whole REST side (versions, traits, process documents, archive) runs
end to end by frontend/tests/e2e/legacy-import.spec.ts on the fixture old
install (frontend/tests/fixtures/legacy).
"""
import json
import sqlite3
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from gemini.importers.gemi_legacy.processing import (
    Importer,
    as_int,
    canonical_boundaries,
    plan_processing,
    selections_from_csv,
    ws_tag,
)
from gemini.importers.gemi_legacy.reader import LegacyDatabase, LegacyPlotRecord, LegacyTraitRecord

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


# ── The REST side of trait sets and reference data, over a fake server ──

class _Resp:
    def __init__(self, body, method, url, status=200):
        self.status_code, self._body, self.url = status, body, url
        self.request = SimpleNamespace(method=method)
        self.content = b"x" if body is not None else b""
        self.text = str(body)

    def json(self):
        return self._body


class FakeServer:
    """Datasets, traits, trait records and reference data: enough for
    Importer._traits and Importer.reference_datasets."""

    def __init__(self):
        self.datasets: dict[str, dict] = {}
        self.traits: dict[str, dict] = {}
        self.records: list[dict] = []
        self.reference: list[dict] = []
        self.calls: list[tuple[str, str]] = []

    def get(self, url, params=None):
        self.calls.append(("GET", url))
        params = params or {}
        if url == "/api/datasets":
            rows = [d for d in self.datasets.values() if d["dataset_name"] == params.get("dataset_name")]
            return _Resp(rows, "GET", url, 200 if rows else 404)
        if url == "/api/traits":
            rows = [t for t in self.traits.values() if t["trait_name"] == params.get("trait_name")]
            return _Resp(rows, "GET", url, 200 if rows else 404)
        if url == "/api/reference_data":
            return _Resp(self.reference, "GET", url)
        raise AssertionError(url)

    def post(self, url, json=None, params=None, files=None):
        self.calls.append(("POST", url))
        if url == "/api/datasets":
            row = {**json, "id": str(uuid.uuid4())}
            self.datasets[row["id"]] = row
            return _Resp(row, "POST", url)
        if url == "/api/traits":
            row = {**json, "id": str(uuid.uuid4())}
            self.traits[row["id"]] = row
            return _Resp(row, "POST", url)
        if url.endswith("/records/bulk"):
            for r in json["records"]:
                # Like TraitRecord.create: row/col need a plot number.
                if r.get("plot_number") is None and (r.get("plot_row_number") or r.get("plot_column_number")):
                    return _Resp({"detail": "plot_number is required"}, "POST", url, 400)
                self.records.append({**r, "dataset_name": json["dataset_name"]})
            return _Resp({"ok": True}, "POST", url)
        if url == "/api/reference_data/upload":
            self.reference.append({"name": params["name"],
                                   "dataset_info": {"legacy_reference_id": params.get("legacy_reference_id")}})
            return _Resp({"ok": True}, "POST", url)
        raise AssertionError(url)

    def patch(self, url, json=None):
        self.calls.append(("PATCH", url))
        self.datasets[url.rsplit("/", 1)[1]].update(json)
        return _Resp({"ok": True}, "PATCH", url)

    def delete(self, url):
        self.calls.append(("DELETE", url))
        ds = self.datasets.pop(url.rsplit("/", 1)[1])
        self.records = [r for r in self.records if r["dataset_name"] != ds["dataset_name"]]
        return _Resp(None, "DELETE", url)


SCOPE = {"season": "2025", "experiment": "E", "site": "L", "population": "P",
         "date": "2025-06-10", "platform": "Drone", "sensor": "RGB"}


def _importer(tmp_path, server):
    path = tmp_path / "gemi.db"
    db = LegacyDatabase(path if path.exists() else make_db(path))
    return Importer(db, tmp_path, server, storage=None, bucket="gemini", progress=lambda _m: None)


def _trait_set():
    tr = LegacyTraitRecord("aa" * 16, "run", 1, ["Height"], 1, 1, "2025-06-11")
    rows = [LegacyPlotRecord(tr.id, "1", "CB27", "1", "2", {"Height": 10.0}),
            LegacyPlotRecord(tr.id, "5A", None, "3", "4", {"Height": 12.5}),
            LegacyPlotRecord(tr.id, "2", None, "1", "3", {})]  # no value: skipped
    return tr, rows


def test_trait_values_with_odd_plot_ids_are_kept_unlinked(tmp_path):
    server = FakeServer()
    imp = _importer(tmp_path, server)
    tr, rows = _trait_set()
    assert imp._traits(tr, rows, SCOPE) is True
    linked, unlinked = sorted(server.records, key=lambda r: r["plot_number"] is None)
    assert (linked["plot_number"], linked["plot_row_number"], linked["plot_column_number"]) == (1, 1, 2)
    assert (unlinked["plot_number"], unlinked["plot_row_number"], unlinked["plot_column_number"]) == (None,) * 3
    assert {k: unlinked["record_info"][k] for k in ("legacy_plot_id", "legacy_row", "legacy_col")} == {
        "legacy_plot_id": "5A", "legacy_row": "3", "legacy_col": "4"}
    (ds,) = server.datasets.values()
    assert ds["dataset_info"]["import_complete"] is True
    assert len(imp.result["notes"]) == 1 and "1 trait value(s)" in imp.result["notes"][0]


def test_an_interrupted_trait_set_is_redone_and_a_finished_one_skipped(tmp_path):
    server = FakeServer()
    tr, rows = _trait_set()
    _importer(tmp_path, server)._traits(tr, rows, SCOPE)
    # Interrupted: the dataset is there, with some records, but not marked.
    (ds,) = server.datasets.values()
    ds["dataset_info"].pop("import_complete")
    server.records = server.records[:1]
    assert _importer(tmp_path, server)._traits(tr, rows, SCOPE) is True
    assert ("DELETE", f"/api/datasets/id/{ds['id']}") in server.calls
    assert len(server.records) == 2 and len(server.datasets) == 1
    # Finished: nothing is written.
    server.calls.clear()
    assert _importer(tmp_path, server)._traits(tr, rows, SCOPE) is False
    assert [c for c in server.calls if c[0] != "GET"] == []
    assert len(server.records) == 2


def test_reference_datasets_with_the_same_name_both_import_once(tmp_path):
    db_path = make_db(tmp_path / "gemi.db")
    conn = sqlite3.connect(db_path)
    for rid in (uuid.uuid4().hex, uuid.uuid4().hex):
        conn.execute("INSERT INTO referencedataset (id, name, experiment, location, population, date, "
                     "column_mapping, plot_count, trait_columns, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (rid, "Yield", "E", "L", "P", "2025-06-10", "{}", 0, '["Yield"]', "2025-06-10"))
    conn.commit()
    conn.close()
    server = FakeServer()
    for _ in range(2):
        with LegacyDatabase(db_path) as db:
            imp = Importer(db, tmp_path, server, storage=None, bucket="gemini", progress=lambda _m: None)
            imp.reference_datasets()
    assert [r["name"] for r in server.reference] == ["Yield", "Yield"]
    assert len({r["dataset_info"]["legacy_reference_id"] for r in server.reference}) == 2
    assert imp.result["reference_datasets"] == 0 and imp.result["failed"] == []
