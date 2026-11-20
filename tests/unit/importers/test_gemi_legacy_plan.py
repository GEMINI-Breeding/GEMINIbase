"""Old-GEMI importer: reading gemi.db and planning tier-1 uploads.

Databases are built from the exact schemas the old app's own code created
(tests/fixtures/gemi_legacy/schema-*.sql, captured from each tag's
SQLModel create_all), so column drift between versions is real.
"""
import sqlite3
import uuid
from pathlib import Path

import pytest

from gemini.importers.gemi_legacy.plan import SHORT_ID, plan_import, season_of
from gemini.importers.gemi_legacy.reader import (
    LegacyDatabase,
    norm_rel_path,
    norm_uuid,
    open_readonly,
)

FIXTURES = Path(__file__).parents[2] / "fixtures" / "gemi_legacy"


def make_db(path: Path, version: str = "v0.0.5", drop: tuple[str, str] | None = None) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript((FIXTURES / f"schema-{version}.sql").read_text())
    if drop:  # a pre-release database, before an ad-hoc ALTER TABLE added a column
        conn.execute(f'ALTER TABLE {drop[0]} DROP COLUMN {drop[1]}')
    conn.commit()
    conn.close()
    return path


def add_upload(path: Path, storage_path: str, data_type: str = "Image Data", status: str = "completed",
               experiment: str = "GEMINI", date: str = "2026-03-10", **extra) -> str:
    uid = uuid.uuid4().hex  # stored the old app's way: 32 hex, no dashes
    conn = sqlite3.connect(path)
    cols = {c[1] for c in conn.execute("PRAGMA table_info(fileupload)")}
    row = {
        "id": uid, "owner_id": uuid.uuid4().hex, "data_type": data_type,
        "experiment": experiment, "location": "Davis", "population": "Cowpea MAGIC",
        "date": date, "platform": "Drone", "sensor": "RGB", "storage_path": storage_path,
        "msgs_synced_path": None, "file_count": 0, "status": status,
        "created_at": "2026-04-27T23:56:31.051091", **extra,
    }
    row = {k: v for k, v in row.items() if k in cols}
    conn.execute(
        f"INSERT INTO fileupload ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})",
        list(row.values()),
    )
    conn.commit()
    conn.close()
    return str(uuid.UUID(uid))


def touch(root: Path, rel: str, size: int = 10) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x" * size)


IMG = "Raw/2026/GEMINI/Davis/Cowpea MAGIC/2026-03-10/Drone/RGB/Images"


# ── Reading ─────────────────────────────────────────────────────────────


def test_the_database_cannot_be_written(tmp_path):
    db = make_db(tmp_path / "gemi.db")
    conn = open_readonly(db)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM fileupload")
    conn.close()
    # And no journal/WAL file appeared beside it.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["gemi.db"]


@pytest.mark.parametrize("version", ["v0.0.3", "v0.0.5"])
def test_reads_each_released_schema(tmp_path, version):
    db = make_db(tmp_path / "gemi.db", version)
    uid = add_upload(db, IMG)
    with LegacyDatabase(db) as legacy:
        (u,) = legacy.uploads()
    assert u.id == uid and u.storage_path == IMG and u.experiment == "GEMINI"


def test_a_column_added_after_release_may_be_missing(tmp_path):
    db = make_db(tmp_path / "gemi.db", "v0.0.3", drop=("fileupload", "msgs_synced_path"))
    add_upload(db, IMG)
    with LegacyDatabase(db) as legacy:
        (u,) = legacy.uploads()
        assert u.msgs_synced_path is None
        assert legacy.rows("referencedataset", ["id", "original_filename"]) == []


def test_json_columns_are_parsed_and_bad_json_is_none(tmp_path):
    db = make_db(tmp_path / "gemi.db")
    conn = sqlite3.connect(db)
    for i, cfg in enumerate(['{"odm_preset": "draft"}', "{not json"]):
        conn.execute(
            "INSERT INTO pipeline (id, workspace_id, name, type, config, created_at) VALUES (?,?,?,?,?,?)",
            (uuid.uuid4().hex, uuid.uuid4().hex, f"p{i}", "aerial", cfg, "2026-01-01"),
        )
    conn.commit()
    conn.close()
    with LegacyDatabase(db) as legacy:
        configs = [r["config"] for r in legacy.rows("pipeline", ["name", "config"])]
    assert configs == [{"odm_preset": "draft"}, None]


def test_uuid_forms():
    u = uuid.uuid4()
    assert norm_uuid(u.hex) == norm_uuid(str(u)) == norm_uuid(u.bytes) == str(u)
    assert norm_uuid("") is None and norm_uuid("nope") is None


@pytest.mark.parametrize("stored, old_root, expected", [
    ("Raw/2026/E/L/P", None, "Raw/2026/E/L/P"),
    ("Raw\\2026\\E\\L\\P", None, "Raw/2026/E/L/P"),                      # Windows separators
    ("./Raw/2026//E/", None, "Raw/2026/E"),
    ("/Users/ann/GEMI-Data/Raw/2026/E", "/Users/ann/GEMI-Data", "Raw/2026/E"),
    ("C:\\Users\\Ann\\GEMI-Data\\Raw\\2026", "C:\\Users\\Ann\\GEMI-Data", "Raw/2026"),
    ("c:\\users\\ann\\gemi-data\\Raw", "C:\\Users\\Ann\\GEMI-Data", "Raw"),  # case-insensitive on Windows
    ("/etc/passwd", "/Users/ann/GEMI-Data", None),                        # absolute, elsewhere
    ("D:\\other\\Raw", "C:\\Users\\Ann\\GEMI-Data", None),
    ("Raw/../../etc", None, None),                                         # escapes the data folder
    ("", None, None),
])
def test_paths_are_made_safe_and_relative(stored, old_root, expected):
    assert norm_rel_path(stored, old_root) == expected


# ── Planning ────────────────────────────────────────────────────────────


def test_image_upload_gets_the_dataset_segment_and_keeps_its_place(tmp_path):
    data = tmp_path / "GEMI-Data"
    touch(data, f"{IMG}/DJI_0001.JPG", 100)
    touch(data, f"{IMG}/sub/DJI_0002.JPG", 50)
    db = make_db(tmp_path / "gemi.db")
    uid = add_upload(db, IMG)
    with LegacyDatabase(db) as legacy:
        plan = plan_import(legacy, data)
    (u,) = plan.to_import
    assert (u.upload_id, u.season, u.site, u.population) == (uid, "2026", "Davis", "Cowpea MAGIC")
    assert u.needs_dataset and u.bytes == 150
    base = "Raw/2026/GEMINI/Davis/Cowpea MAGIC/2026-03-10/Drone/RGB"
    assert [f.target for f in u.files] == [
        f"{base}/{SHORT_ID}/Images/DJI_0001.JPG",
        f"{base}/{SHORT_ID}/Images/sub/DJI_0002.JPG",
    ]
    assert plan.summary()["files"] == 2 and plan.summary()["experiments"] == ["GEMINI"]


def test_season_is_the_old_paths_year_slot_even_if_the_date_disagrees(tmp_path):
    db = make_db(tmp_path / "gemi.db")
    add_upload(db, "Raw/2022/GEMINI/Davis/Cowpea MAGIC/2026-03-10/Drone/RGB/Images")
    with LegacyDatabase(db) as legacy:
        (u,) = legacy.uploads()
    assert season_of(u) == "2022"


def test_dem_moves_to_its_own_folder_and_rgb_stays(tmp_path):
    data = tmp_path / "d"
    ortho = "Raw/2026/E/L/P/2026-03-10/Drone/RGB/Orthomosaic"
    touch(data, f"{ortho}/2026-03-10-RGB.tif")
    touch(data, f"{ortho}/2026-03-10-DEM.tif")
    db = make_db(tmp_path / "gemi.db")
    add_upload(db, ortho, data_type="Orthomosaic", experiment="E")
    with LegacyDatabase(db) as legacy:
        (u,) = plan_import(legacy, data).to_import
    assert sorted(f.target for f in u.files) == [
        "Raw/2026/E/L/P/2026-03-10/Drone/RGB/Orthomosaic-DEM/2026-03-10-DEM.tif",
        "Raw/2026/E/L/P/2026-03-10/Drone/RGB/Orthomosaic/2026-03-10-RGB.tif",
    ]
    assert not u.needs_dataset


def test_amiga_extraction_is_laid_out_like_the_new_extractor(tmp_path):
    data = tmp_path / "d"
    amiga = "Raw/2026/E/L/P/2026-07-15/Amiga/RGB/Images"
    touch(data, f"{amiga}/RGB/top/frame_1.jpg")
    touch(data, f"{amiga}/RGB/Metadata/msgs_synced.csv")
    db = make_db(tmp_path / "gemi.db")
    add_upload(db, amiga, data_type="Farm-ng Binary File", experiment="E")
    with LegacyDatabase(db) as legacy:
        (u,) = plan_import(legacy, data).to_import
    root = f"Raw/2026/E/L/P/2026-07-15/Amiga/RGB/{SHORT_ID}"
    assert sorted(f.target for f in u.files) == [
        f"{root}/RGB/Images/top/frame_1.jpg",
        f"{root}/RGB/Metadata/msgs_synced.csv",
    ]


def test_field_design_and_logs_keep_their_paths(tmp_path):
    data = tmp_path / "d"
    touch(data, "Raw/2026/E/L/P/FieldDesign/design.csv")
    touch(data, "Raw/2026/E/L/P/2026-03-10/Drone/RGB/Metadata/00000001.BIN")
    db = make_db(tmp_path / "gemi.db")
    add_upload(db, "Raw/2026/E/L/P/FieldDesign", data_type="Field Design", experiment="E")
    add_upload(db, "Raw/2026/E/L/P/2026-03-10/Drone/RGB/Metadata", data_type="Ardupilot Logs", experiment="E")
    with LegacyDatabase(db) as legacy:
        targets = sorted(f.target for u in plan_import(legacy, data).to_import for f in u.files)
    assert targets == [
        "Raw/2026/E/L/P/2026-03-10/Drone/RGB/Metadata/00000001.BIN",
        "Raw/2026/E/L/P/FieldDesign/design.csv",
    ]


def test_uploads_that_cannot_be_imported_say_why(tmp_path):
    data = tmp_path / "d"
    (data / "Raw/2026/E/L/P/2026-01-01/Drone/RGB/Images").mkdir(parents=True)  # empty
    db = make_db(tmp_path / "gemi.db")
    add_upload(db, "Raw/2026/E/L/P/2026-01-01/Drone/RGB/Images", experiment="E")
    add_upload(db, "Raw/2026/E/L/P/gone/Drone/RGB/Images", experiment="E")
    add_upload(db, "Raw/2026/E/L/P/x/Drone/RGB/Images", status="missing", experiment="E")
    add_upload(db, "../outside", experiment="E")
    add_upload(db, "Raw/2026/E/L/P/x/Genome", data_type="Genotype Calls", experiment="E")
    with LegacyDatabase(db) as legacy:
        plan = plan_import(legacy, data)
    reasons = sorted(s["reason"] for s in plan.summary()["skipped"])
    assert plan.to_import == []
    assert reasons == [
        "its folder is empty",
        "its folder is not in the data folder",
        "no usable folder path in the old database",
        "the old app had already marked its folder missing",
        "unknown data type 'Genotype Calls'",
    ]


def test_a_symlink_out_of_the_upload_folder_is_not_followed(tmp_path):
    data = tmp_path / "d"
    touch(data, f"{IMG}/ok.jpg")
    touch(tmp_path, "secret.txt")
    (data / IMG / "link.txt").symlink_to(tmp_path / "secret.txt")
    db = make_db(tmp_path / "gemi.db")
    add_upload(db, IMG)
    with LegacyDatabase(db) as legacy:
        (u,) = plan_import(legacy, data).to_import
    assert [f.source.rsplit("/", 1)[-1] for f in u.files] == ["ok.jpg"]
