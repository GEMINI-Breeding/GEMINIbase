"""
Extract the embedded thermal payload from a FLIR One Pro–class JPEG.

These files are RGB JPEGs with a FLIR APP1 block that carries:
  - An embedded `RawThermalImage` (PNG, 16-bit single-channel) holding
    the raw signal counts in MSB-first byte order.
  - Planck calibration constants (PlanckR1, B, F, O, R2).
  - Ambient correction values (Emissivity, ObjectDistance,
    ReflectedApparentTemperature, AtmosphericTemperature, etc.).
  - Optional GPS in the parent EXIF.

Exiftool is the only general-purpose tool that knows how to walk this
APP1 structure, so we shell out to it. The Docker image installs the
`exiftool` package.
"""
from __future__ import annotations

import io
import json
import subprocess
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

from gemini.workers.thermal.calibration import PlanckParams


@dataclass
class FlirJpegPayload:
    """All the per-file values the thermal worker needs from a FLIR JPEG."""

    raw_counts: np.ndarray  # uint16 HxW
    planck: PlanckParams
    emissivity: float
    has_gps: bool
    raw_thermal_image_type: str  # "PNG" or "TIFF"


def _run_exiftool_json(path: str) -> dict[str, Any]:
    """Invoke `exiftool -j -a -G1` and parse the single-record JSON."""
    proc = subprocess.run(
        ["exiftool", "-j", "-a", "-G1", path],
        check=True,
        capture_output=True,
        text=True,
    )
    parsed = json.loads(proc.stdout)
    if not parsed:
        raise RuntimeError(f"exiftool returned no records for {path}")
    return parsed[0]


def _exiftool_extract_bytes(path: str, tag: str) -> bytes:
    """Invoke `exiftool -b -<tag>` and return the raw bytes."""
    proc = subprocess.run(
        ["exiftool", "-b", f"-{tag}", path],
        check=True,
        capture_output=True,
    )
    return proc.stdout


def _coerce_float(val: Any, *, default: float | None = None) -> float:
    """Parse a FLIR EXIF value like '17450.25', '1435', '1.00' to a float."""
    if val is None:
        return float("nan") if default is None else default
    if isinstance(val, (int, float)):
        return float(val)
    # exiftool sometimes returns "1.00 m" or "22.0 C" — take the leading float.
    s = str(val).strip().split()[0]
    return float(s)


def extract_flir_jpeg(path: str) -> FlirJpegPayload:
    """Read a FLIR One Pro–class JPEG and return its thermal payload.

    Raises if the file doesn't carry a RawThermalImage block — that's
    the marker that distinguishes a radiometric FLIR JPEG from a plain
    photo with a FLIR Systems EXIF Make string. The worker uses this
    to fail loudly when a user mis-classifies a regular JPEG as thermal.
    """
    meta = _run_exiftool_json(path)
    if not any(k.endswith(":RawThermalImage") for k in meta):
        raise RuntimeError(
            f"{path}: no RawThermalImage in EXIF; not a FLIR-One-Pro thermal JPEG"
        )

    raw_bytes = _exiftool_extract_bytes(path, "RawThermalImage")
    img = Image.open(io.BytesIO(raw_bytes))
    # The embedded image is uint16 single-channel. PIL exposes it as mode "I;16".
    if img.mode not in ("I;16", "I;16B", "I;16L", "I"):
        raise RuntimeError(
            f"{path}: unexpected RawThermalImage mode {img.mode!r}"
        )
    arr = np.asarray(img, dtype=np.uint16)

    planck = PlanckParams(
        r1=_coerce_float(_get_tag(meta, "PlanckR1")),
        b=_coerce_float(_get_tag(meta, "PlanckB")),
        f=_coerce_float(_get_tag(meta, "PlanckF")),
        o=_coerce_float(_get_tag(meta, "PlanckO")),
        r2=_coerce_float(_get_tag(meta, "PlanckR2")),
    )
    emissivity = _coerce_float(_get_tag(meta, "Emissivity"), default=1.0)
    if not (0.0 < emissivity <= 1.0):
        emissivity = 1.0

    # GPS presence: the parent EXIF (or the APP1 GPS block) carries
    # GPSLatitude. drone_low_res has it; amiga_low_res does too. We
    # only need to know yes/no so the orthomosaic preflight (Phase D)
    # can refuse early when GPS is missing.
    has_gps = any(
        k.endswith(":GPSLatitude") and meta[k] not in (None, "")
        for k in meta
    )

    raw_type = str(_get_tag(meta, "RawThermalImageType") or "PNG")
    return FlirJpegPayload(
        raw_counts=arr,
        planck=planck,
        emissivity=emissivity,
        has_gps=has_gps,
        raw_thermal_image_type=raw_type,
    )


def _get_tag(meta: dict[str, Any], tag: str) -> Any:
    """Find an exiftool group-prefixed key whose suffix matches `tag`."""
    for k, v in meta.items():
        if k.split(":", 1)[-1] == tag:
            return v
    return None
