"""Several .bin logs in one upload: each extraction merges its metadata
with what the earlier ones wrote (gemini.workers.amiga.worker)."""
import io

import pandas as pd

from gemini.workers.amiga.worker import merge_with_existing


class FakeObject(io.BytesIO):
    def release_conn(self):
        pass


class FakeClient:
    def __init__(self, objects):
        self.objects = objects

    def get_object(self, bucket, name):
        if name not in self.objects:
            raise KeyError(name)
        return FakeObject(self.objects[name])


def track(stamps, lat0):
    return pd.DataFrame({
        "/top/rgb": stamps,
        "stamp": stamps,
        "lat": [lat0 - i * 1e-6 for i in range(len(stamps))],
        "lon": [-121.7] * len(stamps),
        "/top/rgb_file": [f"/top/rgb-{s}.jpg" for s in stamps],
    })


def test_second_log_is_merged_into_the_first(tmp_path):
    parent = "Raw/S/E/L/P/D/Amiga/RGB/aaaa1111"
    first = track([100, 101, 102], 38.5)
    client = FakeClient({
        f"{parent}/RGB/Metadata/msgs_synced.csv": first.to_csv(index=False).encode(),
        f"{parent}/report.txt": b"--- File: first.bin ---\n",
    })
    out = tmp_path / "out"
    (out / "RGB/Metadata").mkdir(parents=True)
    # The later log, plus one frame the first log also had (a re-run).
    track([102, 200, 201], 38.49).to_csv(out / "RGB/Metadata/msgs_synced.csv", index=False)
    (out / "report.txt").write_text("--- File: second.bin ---\n")

    merge_with_existing(client, out, parent)

    merged = pd.read_csv(out / "RGB/Metadata/msgs_synced.csv")
    assert merged["stamp"].tolist() == [100, 101, 102, 200, 201]
    assert "direction" in merged.columns
    report = (out / "report.txt").read_text()
    assert "first.bin" in report and "second.bin" in report


def test_first_log_is_left_alone(tmp_path):
    out = tmp_path / "out"
    (out / "RGB/Metadata").mkdir(parents=True)
    track([1, 2], 38.5).to_csv(out / "RGB/Metadata/msgs_synced.csv", index=False)
    merge_with_existing(FakeClient({}), out, "Raw/x")
    assert pd.read_csv(out / "RGB/Metadata/msgs_synced.csv")["stamp"].tolist() == [1, 2]
