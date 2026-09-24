"""Old-GEMI importer: carrying out a plan (entities, dataset, files).

The REST session and storage are fakes that record calls; the real stack
path is covered by frontend/tests/e2e/legacy-import.spec.ts.
"""
import uuid
from types import SimpleNamespace

from gemini.importers.gemi_legacy.plan import SHORT_ID, ImportPlan, PlannedFile, UploadPlan
from gemini.importers.gemi_legacy.run import dataset_name, run_import


class FakeResponse:
    def __init__(self, status, body, method="GET", url=""):
        self.status_code, self._body = status, body
        self.content = b"x"
        self.text = str(body)
        self.request = SimpleNamespace(method=method)
        self.url = url

    def json(self):
        return self._body


class FakeApi:
    """Just enough of the REST API: find-by-name and create per route."""

    def __init__(self, fail_route=None):
        self.rows: dict[str, list[dict]] = {}
        self.posts: list[tuple[str, dict]] = []
        self.fail_route = fail_route

    def get(self, route, params=None):
        name_key = next((k for k in (params or {}) if k.endswith("_name") and k != "experiment_name"), None)
        if name_key is None:
            name_key = "experiment_name"
        rows = [r for r in self.rows.get(route, []) if r.get(name_key) == params[name_key]]
        return FakeResponse(200 if rows else 404, rows, "GET", route)

    def post(self, route, json=None):
        self.posts.append((route, json))
        if route == self.fail_route:
            return FakeResponse(500, {"error": "boom"}, "POST", route)
        if route in ("/api/files/register_batch", "/api/users/me/experiments"):
            return FakeResponse(200, {"status": "ok"}, "POST", route)
        row = {**json, "id": str(uuid.uuid4())}
        self.rows.setdefault(route, []).append(row)
        return FakeResponse(200, row, "POST", route)


class FakeStorage:
    def __init__(self):
        self.objects: dict[str, int] = {}
        self.types: dict[str, str] = {}
        self.puts: list[str] = []

    def stat_object(self, bucket, key):
        if key not in self.objects:
            raise KeyError(key)
        return SimpleNamespace(size=self.objects[key])

    def fput_object(self, bucket, key, path, content_type="application/octet-stream"):
        from pathlib import Path

        self.objects[key] = Path(path).stat().st_size
        self.types[key] = content_type
        self.puts.append(key)


def upload(tmp_path, uid="11111111-2222-3333-4444-555555555555", data_type="Image Data",
           sensor="RGB", files=("a.jpg", "b.jpg"), date="2025-06-10", experiment="Trial"):
    src = "Raw/2025/Trial/Davis/Pop/2025-06-10/Drone/RGB/Images"
    planned = []
    for name in files:
        p = tmp_path / src / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"12345")
        planned.append(PlannedFile(f"{src}/{name}", f"Raw/2025/Trial/Davis/Pop/2025-06-10/Drone/RGB/{SHORT_ID}/Images/{name}", 5))
    return UploadPlan(
        upload_id=uid, data_type=data_type, season="2025", experiment=experiment, site="Davis",
        population="Pop", date=date, platform="Drone", sensor=sensor, source_dir=src,
        created_at="2025-06-11T09:15:00", files=planned,
    )


def test_an_upload_becomes_what_the_uploader_would_create(tmp_path):
    api, storage = FakeApi(), FakeStorage()
    result = run_import(ImportPlan([upload(tmp_path)]), tmp_path, api, storage, "gemini")
    routes = [r for r, _ in api.posts]
    assert routes == [
        "/api/experiments", "/api/users/me/experiments", "/api/seasons", "/api/sites",
        "/api/populations", "/api/sensor_platforms", "/api/sensors", "/api/datasets",
        "/api/files/register_batch",
    ]
    sensor = dict(api.posts)["/api/sensors"]
    assert sensor["sensor_type_id"] == 1 and sensor["sensor_platform_name"] == "Drone"
    ds = dict(api.posts)["/api/datasets"]
    assert ds["dataset_name"] == "Trial__ImageData__20250611__091500__11111111"
    assert ds["collection_date"] == "2025-06-10T00:00:00"
    assert ds["dataset_info"]["legacy_upload_id"] == "11111111-2222-3333-4444-555555555555"
    (imp,) = result["imported"]
    short = imp["dataset_id"].replace("-", "")[:8]
    assert sorted(storage.objects) == [
        f"Raw/2025/Trial/Davis/Pop/2025-06-10/Drone/RGB/{short}/Images/a.jpg",
        f"Raw/2025/Trial/Davis/Pop/2025-06-10/Drone/RGB/{short}/Images/b.jpg",
    ]
    registered = dict(api.posts)["/api/files/register_batch"]
    assert registered["dataset_id"] == imp["dataset_id"]
    assert sorted(f["object_name"] for f in registered["files"]) == sorted(storage.objects)
    assert (imp["copied"], imp["already_there"]) == (2, 0)
    # Stored with the type a browser upload records, not octet-stream.
    assert set(storage.types.values()) == {"image/jpeg"}


def test_running_again_resumes_without_duplicates(tmp_path):
    api, storage = FakeApi(), FakeStorage()
    plan = ImportPlan([upload(tmp_path)])
    first = run_import(plan, tmp_path, api, storage, "gemini")
    # A fresh run (new process): nothing cached, everything found instead.
    second = run_import(plan, tmp_path, FakeApiSharing(api), storage, "gemini")
    assert len(api.rows["/api/datasets"]) == 1 and len(api.rows["/api/experiments"]) == 1
    assert second["imported"][0]["dataset_id"] == first["imported"][0]["dataset_id"]
    assert (second["imported"][0]["copied"], second["imported"][0]["already_there"]) == (0, 2)
    assert len(storage.puts) == 2


def FakeApiSharing(api):  # a new client over the same "server" state
    fresh = FakeApi()
    fresh.rows, fresh.posts = api.rows, api.posts
    return fresh


def test_a_partly_copied_file_is_copied_again(tmp_path):
    api, storage = FakeApi(), FakeStorage()
    plan = ImportPlan([upload(tmp_path)])
    run_import(plan, tmp_path, api, storage, "gemini")
    truncated = storage.puts[0]
    storage.objects[truncated] = 2  # interrupted mid-copy
    result = run_import(plan, tmp_path, FakeApiSharing(api), storage, "gemini")
    assert result["imported"][0]["copied"] == 1 and storage.puts[-1] == truncated


def test_one_failing_upload_does_not_stop_the_others(tmp_path):
    api, storage = FakeApi(fail_route=None), FakeStorage()
    bad = upload(tmp_path, uid="22222222-0000-0000-0000-000000000000", experiment="Broken")
    good = upload(tmp_path)
    # The broken one's experiment can't be created.
    original_post = api.post
    api.post = lambda route, json=None: (
        FakeResponse(500, {"error": "boom"}, "POST", route)
        if route == "/api/experiments" and json.get("experiment_name") == "Broken"
        else original_post(route, json)
    )
    result = run_import(ImportPlan([bad, good]), tmp_path, api, storage, "gemini")
    assert [f["upload_id"] for f in result["failed"]] == [bad.upload_id]
    assert "500" in result["failed"][0]["error"]
    assert [i["upload_id"] for i in result["imported"]] == [good.upload_id]


def test_thermal_is_classified_and_reported(tmp_path):
    api, storage = FakeApi(), FakeStorage()
    result = run_import(ImportPlan([upload(tmp_path, sensor="FLIR Thermal")]), tmp_path, api, storage, "gemini")
    assert dict(api.posts)["/api/sensors"]["sensor_type_id"] == 3
    assert result["thermal_uploads"] == [result["imported"][0]["path"]]


def test_dataset_name_is_stable_and_like_the_uploaders(tmp_path):
    u = upload(tmp_path)
    assert dataset_name(u) == dataset_name(u) == "Trial__ImageData__20250611__091500__11111111"
    u.created_at = None
    assert dataset_name(u).endswith("__00000000__000000__11111111")


def test_cancelling_stops_before_the_next_upload(tmp_path):
    api, storage = FakeApi(), FakeStorage()
    a = upload(tmp_path)
    b = upload(tmp_path, uid="33333333-0000-0000-0000-000000000000", experiment="Other")
    calls = {"n": 0}

    def cancelled():
        calls["n"] += 1
        return calls["n"] > 1

    result = run_import(ImportPlan([a, b]), tmp_path, api, storage, "gemini", cancelled=cancelled)
    assert [i["upload_id"] for i in result["imported"]] == [a.upload_id]
    assert result["cancelled"] is True
