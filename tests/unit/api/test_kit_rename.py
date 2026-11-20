"""Renaming a platform or sensor of data already in the app: which paths, and how."""
import pytest

from gemini.api.kit_rename import Rename, new_path, rewrite_json, rewrite_text

pytestmark = pytest.mark.unit

R = Rename(experiment="Interspecific Kearney", field="platform", old="P4", new="Drone")
BASE = "2022/Interspecific Kearney/Kearney/Interspecific/2022-07-05"


def test_paths_of_the_renamed_data_move():
    assert new_path(f"Raw/{BASE}/P4/RGB/Orthomosaic/a.tif", R) == f"Raw/{BASE}/Drone/RGB/Orthomosaic/a.tif"
    assert new_path(f"Processed/{BASE}/P4/RGB/PlotImages/p1.png", R) == \
        f"Processed/{BASE}/Drone/RGB/PlotImages/p1.png"
    assert new_path(f"gemini/Raw/{BASE}/P4/RGB/x.tif", R) == f"gemini/Raw/{BASE}/Drone/RGB/x.tif"
    assert new_path(f"Processed/{BASE}/P4/RGB/", R) == f"Processed/{BASE}/Drone/RGB/"


def test_other_data_is_left_alone():
    assert new_path(f"Raw/2022/GEMINI/Kearney/Interspecific/2022-07-05/P4/RGB/a.tif", R) is None   # other experiment
    assert new_path(f"Raw/{BASE}/Drone/RGB/a.tif", R) is None
    assert new_path(f"Raw/{BASE}/P4", R) == f"Raw/{BASE}/Drone"    # the platform's folder itself
    assert new_path("Models/weights/P4.pt", R) is None
    site = Rename(experiment="Interspecific Kearney", field="platform", old="P4", new="Drone", site="Davis")
    assert new_path(f"Raw/{BASE}/P4/RGB/a.tif", site) is None


def test_sensor_rename():
    s = Rename(experiment="E", field="sensor", old="FC6310", new="RGB")
    assert new_path("Raw/2023/E/Davis/Bean/2023-06-01/Drone/FC6310/ab12cd34/Images/x.JPG", s) == \
        "Raw/2023/E/Davis/Bean/2023-06-01/Drone/RGB/ab12cd34/Images/x.JPG"


def test_paths_inside_text_and_documents():
    assert rewrite_text(f"Processed/{BASE}/P4/RGB/odm.tif", R) == f"Processed/{BASE}/Drone/RGB/odm.tif"
    e = Rename(experiment="GEMINI", field="platform", old="Amiga", new="Rover")
    assert rewrite_text("saved to Processed/2025/GEMINI/Davis/Bean/2025-06-01/Amiga/RGB/x.png today", e) == \
        "saved to Processed/2025/GEMINI/Davis/Bean/2025-06-01/Rover/RGB/x.png today"
    run = {"id": "r1", "name": "2022-07-05 · P4/RGB",
           "uploadScope": {"experiment": "Interspecific Kearney", "location": "Kearney", "population": "Interspecific",
                           "date": "2022-07-05", "platform": "P4", "sensor": "RGB"},
           "steps": {"orthomosaic": {"outputs": {"path": f"Raw/{BASE}/P4/RGB/Orthomosaic/a.tif"}}}}
    out, n = rewrite_json(run, R)
    assert out["uploadScope"]["platform"] == "Drone"
    assert out["steps"]["orthomosaic"]["outputs"]["path"] == f"Raw/{BASE}/Drone/RGB/Orthomosaic/a.tif"
    assert out["name"] == "2022-07-05 · Drone/RGB"
    assert n == 3
    # Another experiment's run named P4 is not touched.
    other = {"uploadScope": {"experiment": "GEMINI", "platform": "P4"}}
    assert rewrite_json(other, R) == (other, 0)


def test_bad_renames_are_refused():
    with pytest.raises(ValueError):
        Rename(experiment="E", field="date", old="a", new="b")
    with pytest.raises(ValueError):
        Rename(experiment="E", field="platform", old="P4", new="P4")
    with pytest.raises(ValueError):
        Rename(experiment="E", field="platform", old="P4", new="Dro/ne")
