"""
Unit tests for `_diagnose_odm_failure` — the helper that turns NodeODM's
generic "Cannot process dataset" into an actionable hint.

Each test uses a small log excerpt taken from a real failed run rather
than a synthetic string, so a future refactor can't pass these tests
without preserving the actual signatures they're meant to detect.
"""
from gemini.workers.odm.worker import _diagnose_odm_failure


# ── Real log tail captured from the 2026-05-07 'Lowest'-preset failure
# (189-image flight, OpenMVS picked 0 images for dense reconstruction
# and DensifyPointCloud segfaulted on the empty result).
OPENMVS_ZERO_IMAGES_LOG = [
    "[INFO]    Running openmvs stage",
    "[INFO]    Depthmap resolution set to: 684px",
    "[INFO]    Running dense reconstruction. This might take a while.",
    "00:52:51 [App     ] Found a camera not pointing towards the scene "
    "center; the scene will be considered unbounded (no ROI)",
    "00:52:51 [App     ] Preparing images for dense reconstruction "
    "completed: 189 images (1s418ms)",
    "00:52:51 [App     ] Selecting images for dense reconstruction "
    "completed: 0 images (70ms)",
    "Fused depth-maps 0 (100%, 0ms)",
    "00:52:51 [App     ] Densifying point-cloud completed: 0 points "
    "(1s497ms)",
    "00:52:51 [App     ] error: no valid point-cloud for the ROI estimation",
    "Segmentation fault",
    "[ERROR]   Uh oh! Processing stopped because of strange values in the "
    "reconstruction.",
]


# Same dataset class but only the 'Negative GSD' / 'unbounded scene' pair —
# this is the EXIF-metadata flavor of failure, distinct from the
# preset-too-aggressive flavor above. The two patterns must not collide.
NEGATIVE_GSD_LOG = [
    "[INFO]    running export_geocoords --reconstruction --proj ...",
    "[WARNING] Negative GSD estimated, this might indicate a flipped Z-axis.",
    "[INFO]    Updating /var/www/data/.../opensfm/config.yaml",
    "00:52:51 [App     ] Found a camera not pointing towards the scene "
    "center; the scene will be considered unbounded (no ROI)",
    "[ERROR]   Reconstruction stopped: invalid scene geometry.",
]


# OOM-killer signature — already covered by the original helper, kept here
# to assert the new patterns don't poach it.
OOM_KILLED_LOG = [
    "[INFO]    Running openmvs stage",
    "[INFO]    Estimating depthmaps",
    "Killed",
    "[ERROR]   Could not compute dense point cloud.",
]


# Real log tail captured from the 2026-05-15 Cowpea MAGIC run on a Mac with
# Docker Desktop at its default ~8 GiB memory / 1 GiB swap. SfM completed
# fully (192-image reconstruction succeeded), but OpenMVS reported only
# 1024 MB of virtual memory, produced 0 depthmaps, and the next stage
# segfaulted (exit 139) on the empty input. NodeODM marked the task FAILED
# with the generic 'Cannot process dataset', and the existing diagnostic
# mis-attributed it to a too-aggressive quality preset.
OPENMVS_LOW_VMEM_LOG = [
    "[INFO]    Running openmvs stage",
    "[INFO]    Depthmap resolution set to: 684px",
    "[INFO]    Running dense reconstruction. This might take a while.",
    "16:12:13 [App     ] OpenMVS x32 v2.2.0",
    "16:12:13 [App     ] CPU:  (12 cores)",
    "16:12:13 [App     ] RAM: 7.65GB Physical Memory 1024.00MB Virtual Memory",
    "16:12:13 [App     ] OS: Linux 6.10.14-linuxkit (aarch64)",
    "16:12:13 [App     ] Found a camera not pointing towards the scene "
    "center; the scene will be considered unbounded (no ROI)",
    "16:12:13 [App     ] Preparing images for dense reconstruction "
    "completed: 192 images (185ms)",
    "16:12:13 [App     ] Selecting images for dense reconstruction "
    "completed: 0 images (56ms)",
    "Fused depth-maps 0 (100%, 0ms)",
    "16:12:13 [App     ] Densifying point-cloud completed: 0 points (245ms)",
    "16:12:13 [App     ] error: no valid point-cloud for the ROI estimation",
    "Segmentation fault",
]


def test_openmvs_rejects_all_images_pattern():
    """The exact 'Selecting images ... completed: 0 images' line must
    surface a quality-preset hint, not the generic 'unknown' fallback.
    This is the bug that motivated the new pattern: 'Lowest' preset on
    a 189-image flight rejected every image and the user got the bare
    'Cannot process dataset' message.
    """
    detail = _diagnose_odm_failure(OPENMVS_ZERO_IMAGES_LOG)
    assert detail, "Expected a non-empty diagnosis for the OpenMVS-0-images case"
    assert "OpenMVS rejected every image" in detail
    # The hint must mention raising the quality preset — that is the
    # actionable next step the user has from the UI.
    assert "Reconstruction quality" in detail or "quality preset" in detail
    assert "Lowest" in detail or "Low" in detail


def test_openmvs_rejects_all_images_via_no_valid_pointcloud_alone():
    """Even if the upstream 'completed: 0 images' line scrolled out of
    the 200-line tail, the ROI-estimation error alone is enough — that
    string only appears when densification has nothing to work with.
    """
    log = ["dummy line"] * 250 + [
        "00:52:51 [App     ] error: no valid point-cloud for the ROI estimation",
        "Segmentation fault",
    ]
    detail = _diagnose_odm_failure(log)
    assert "OpenMVS rejected every image" in detail


def test_negative_gsd_pattern_fires_when_both_warnings_present():
    """`Negative GSD` + `unbounded scene` together imply an EXIF/camera
    issue, not a preset issue. The hint must point at metadata, not
    quality settings.
    """
    detail = _diagnose_odm_failure(NEGATIVE_GSD_LOG)
    assert detail
    assert "EXIF" in detail or "metadata" in detail.lower()
    # Must NOT misclassify as the preset-too-aggressive case.
    assert "OpenMVS rejected every image" not in detail


def test_negative_gsd_alone_does_not_fire():
    """`Negative GSD` on its own is just a warning — ODM logs it on
    plenty of runs that succeed. The pattern requires both signals.
    """
    log = [
        "[WARNING] Negative GSD estimated, this might indicate a flipped Z-axis.",
        "[INFO]    Continuing.",
    ]
    detail = _diagnose_odm_failure(log)
    # Either empty or some other matched pattern; the EXIF-issue hint must
    # not fire from this alone.
    assert "EXIF" not in detail and "metadata" not in detail.lower()


def test_oom_pattern_still_wins_over_zero_images():
    """If the OOM-killer signature is present, it should win — that is
    a more specific, more actionable diagnosis than the OpenMVS-0-images
    fallback. The order of checks in _diagnose_odm_failure encodes this.
    """
    log = OOM_KILLED_LOG + [
        "00:52:51 [App     ] Selecting images for dense reconstruction "
        "completed: 0 images",
    ]
    detail = _diagnose_odm_failure(log)
    assert "out-of-memory" in detail.lower()


def test_unrecognized_failure_returns_empty():
    """The contract is: empty string when nothing matches, so the call
    site can append a 'check the saved log' fallback. Don't regress to
    returning None or raising.
    """
    log = [
        "[INFO]    Some uninteresting line.",
        "[ERROR]   A failure mode we've never seen before.",
    ]
    assert _diagnose_odm_failure(log) == ""


def test_empty_log_returns_empty():
    """No log → no diagnosis. The call site already handles this and
    falls back to NodeODM's generic message + the saved-log pointer.
    """
    assert _diagnose_odm_failure([]) == ""


def test_low_vmem_routes_to_docker_memory_hint():
    """When OpenMVS's own banner shows ~1 GiB virtual memory and the run
    ends in an empty dense cloud, the diagnosis must point at Docker
    Desktop's memory cap, not at the user's quality preset. This is the
    regression: the previous heuristic only inspected the empty-cloud
    symptom and blamed the preset on any Mac with a default Docker
    install, even at the Medium preset.
    """
    detail = _diagnose_odm_failure(OPENMVS_LOW_VMEM_LOG)
    assert detail
    assert "memory" in detail.lower()
    assert "Docker" in detail
    # Must NOT misdirect the user to change quality presets as the
    # primary fix — that was the original wrong message.
    assert "OpenMVS rejected every image" not in detail


def test_high_vmem_with_empty_cloud_still_blames_preset():
    """If memory is clearly not the constraint (large virtual-memory
    figure on the OpenMVS banner) and the dense cloud is still empty,
    the preset-too-aggressive diagnosis is still the right one.
    """
    log = [
        "[INFO]    Running openmvs stage",
        "16:12:13 [App     ] RAM: 64.00GB Physical Memory 32.00GB Virtual Memory",
        "16:12:13 [App     ] Selecting images for dense reconstruction "
        "completed: 0 images (56ms)",
        "16:12:13 [App     ] Densifying point-cloud completed: 0 points",
        "Segmentation fault",
    ]
    detail = _diagnose_odm_failure(log)
    assert "OpenMVS rejected every image" in detail
    assert "quality preset" in detail or "Reconstruction quality" in detail


def test_oom_killer_still_wins_over_low_vmem_branch():
    """The explicit OOM-killer signature ('Killed' + depth-fusion context)
    is more specific than the low-vmem heuristic; it must keep firing
    first so its tailored hint isn't shadowed by the new branch.
    """
    log = OOM_KILLED_LOG + [
        "16:12:13 [App     ] RAM: 7.65GB Physical Memory 1024.00MB Virtual Memory",
        "Densifying point-cloud completed: 0 points",
    ]
    detail = _diagnose_odm_failure(log)
    assert "out-of-memory" in detail.lower()
