"""Moving an upload to a new season/site/population/date/platform/sensor."""
import pytest

from gemini.rest_api import dataset_move as dm

SRC = "Raw/2024/Exp/Davis/Cowpea/2024-07-15/Amiga/RGB/aaaa1111/"
TO = {"season": "2024", "site": "Davis", "population": "Cowpea",
      "date": "2024-07-16", "platform": "Amiga", "sensor": "RGB"}
DST = "Raw/2024/Exp/Davis/Cowpea/2024-07-16/Amiga/RGB/aaaa1111/"


class Store:
    def __init__(self, keys, fail_on=None):
        self.keys = set(keys)
        self.rows = {k: k for k in keys if "Images/" in k}  # registered files
        self.fail_on = fail_on

    def list(self, prefix):
        return sorted(k for k in self.keys if k.startswith(prefix))

    def copy(self, a, b):
        if a == self.fail_on:
            raise OSError("disk full")
        self.keys.add(b)

    def repoint(self, a, b):
        if a in self.rows:
            self.rows[b] = self.rows.pop(a)

    def run(self, folder, to=TO):
        return dm.move_upload(
            folder=folder, to=to, list_objects=self.list, exists=self.keys.__contains__,
            copy=self.copy, remove=self.keys.discard, repoint=self.repoint)


FILES = [SRC + "Images/a.jpg", SRC + "Images/b.jpg", SRC + "Metadata/msgs_synced.csv"]


def test_moves_everything_in_the_upload_folder_and_its_rows():
    store = Store(FILES + ["Processed/2024/Exp/Davis/Cowpea/2024-07-15/Amiga/RGB/ortho.tif"])
    result = store.run(SRC)
    assert result.moved == 3
    assert store.list(SRC) == []
    assert store.list(DST) == [DST + "Images/a.jpg", DST + "Images/b.jpg",
                               DST + "Metadata/msgs_synced.csv"]
    assert sorted(store.rows) == [DST + "Images/a.jpg", DST + "Images/b.jpg"]
    assert result.processed_outputs_left == [
        "Processed/2024/Exp/Davis/Cowpea/2024-07-15/Amiga/RGB/ortho.tif"]


def test_never_overwrites():
    store = Store(FILES + [DST + "Images/a.jpg"])
    with pytest.raises(dm.MoveError, match="already exist") as err:
        store.run(SRC)
    assert err.value.status == 409
    assert len(store.list(SRC)) == 3  # nothing moved


def test_a_failure_stops_and_a_rerun_finishes():
    store = Store(FILES, fail_on=SRC + "Images/b.jpg")
    with pytest.raises(dm.MoveError, match="after moving 1 of 3"):
        store.run(SRC)
    store.fail_on = None
    # The rows now span both folders; the source is still recognisable.
    folder = dm.source_folder(list(store.rows), TO)
    assert folder == SRC
    assert store.run(folder).moved == 2
    assert store.list(SRC) == []


def test_validation():
    with pytest.raises(dm.MoveError, match="date can't be empty"):
        dm.target_folder(SRC, {**TO, "date": " "})
    with pytest.raises(dm.MoveError, match="can't contain"):
        dm.target_folder(SRC, {**TO, "site": "a/b"})
    with pytest.raises(dm.MoveError, match="per-upload folder"):
        dm.source_folder(["Raw/2024/Exp/Davis/Cowpea/2024-07-15/Amiga/RGB/Images/a.jpg"], TO)
    assert dm.move_upload(folder=SRC, to=dm.scope_of(SRC) | {}, list_objects=None,
                          exists=None, copy=None, remove=None, repoint=None).moved == 0


def test_source_folder_of_a_normal_upload():
    assert dm.source_folder([SRC + "Images/a.jpg", SRC + "Images/b.jpg"], {}) == SRC
