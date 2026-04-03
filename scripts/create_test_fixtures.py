"""
One-off script to generate test fixtures from the original sample datasets.

Usage:
    python scripts/create_test_fixtures.py

Requires Pillow:
    pip install Pillow

Sources (adjust paths if needed):
    AMIGA_SOURCE  — Subset Amiga Data directory
    DRONE_SOURCE  — Subset Drone Data directory
"""

import os
import shutil
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("Pillow is required: pip install Pillow")

REPO_ROOT = Path(__file__).parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"

AMIGA_SOURCE = Path.home() / "Downloads" / "Subset Amiga Data" / "2024-07-15" / "Phone"
DRONE_SOURCE = Path.home() / "Downloads" / "Subset Drone Data"

# File numbers to use from the AMIGA dataset (3 representative samples)
AMIGA_SAMPLES = ["00181", "00182", "00183"]

# Image resize dimensions (small enough to keep fixtures tiny, large enough to be valid)
IMAGE_SIZE = (64, 64)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_json(src_dir: Path, dst_dir: Path, samples: list[str]) -> None:
    ensure_dir(dst_dir)
    for number in samples:
        # Find matching JSON file
        matches = list(src_dir.glob(f"*{number}.json"))
        if not matches:
            raise FileNotFoundError(f"No JSON file matching *{number}.json in {src_dir}")
        src = matches[0]
        shutil.copy2(src, dst_dir / src.name)
        print(f"  copied {src.name}")


def resize_jpeg(src: Path, dst: Path, size: tuple) -> None:
    with Image.open(src) as img:
        img = img.convert("RGB")
        img = img.resize(size, Image.LANCZOS)
        img.save(dst, "JPEG", quality=85)
    print(f"  resized {src.name} → {dst.name} ({size[0]}×{size[1]})")


def resize_jpegs(src_dir: Path, dst_dir: Path, samples: list[str], size: tuple) -> None:
    ensure_dir(dst_dir)
    for number in samples:
        matches = list(src_dir.glob(f"*{number}.jpg")) + list(src_dir.glob(f"*{number}.JPG"))
        if not matches:
            raise FileNotFoundError(f"No JPEG file matching *{number}.jpg/JPG in {src_dir}")
        src = matches[0]
        resize_jpeg(src, dst_dir / src.name, size)


def create_empty_dir(path: Path) -> None:
    ensure_dir(path)
    print(f"  created empty dir {path.relative_to(REPO_ROOT)}")


def main():
    print("=== Creating AMIGA fixtures ===")

    amiga_phone = FIXTURES / "amiga" / "Dataset_2024" / "Davis" / "2024-07-15" / "Amiga_Phone" / "Phone"

    # JSON metadata (copy as-is, small files ~740B each)
    print("\nCopying AMIGA metadata JSON files...")
    copy_json(AMIGA_SOURCE / "meta_json", amiga_phone / "meta_json", AMIGA_SAMPLES)

    # RGB JPEGs (downsize)
    print("\nResizing AMIGA RGB JPEGs...")
    resize_jpegs(AMIGA_SOURCE / "rgb_jpeg", amiga_phone / "rgb_jpeg", AMIGA_SAMPLES, IMAGE_SIZE)

    # Optional sensor dirs (empty — parser handles gracefully)
    print("\nCreating empty optional sensor dirs...")
    for dir_name in ("confidence_tiff", "depth_tiff", "flir_jpg"):
        create_empty_dir(amiga_phone / dir_name)

    print("\n=== Creating Drone fixtures ===")

    drone_out = FIXTURES / "drone"

    # CSV files (copy as-is)
    print("\nCopying drone CSV files...")
    for csv_name in ("field_design.csv", "gcp_locations.csv"):
        src = DRONE_SOURCE / csv_name
        shutil.copy2(src, ensure_dir(drone_out) / csv_name)
        print(f"  copied {csv_name}")

    # One image from each date directory
    date_dirs = [
        ("2022-06-27-DavisCowpeaSubset", "2022-06-27_100MEDIA_DJI_0876.JPG"),
        ("2022-07-11-DavisCowpeaSubset", "2022-07-11_100MEDIA_DJI_0002.JPG"),
    ]
    print("\nResizing drone JPEGs...")
    for dir_name, filename in date_dirs:
        src = DRONE_SOURCE / dir_name / filename
        dst_dir = ensure_dir(drone_out / dir_name)
        resize_jpeg(src, dst_dir / filename, IMAGE_SIZE)

    print("\n=== Done ===")
    print(f"Fixtures written to: {FIXTURES}")

    # Print total size
    total = sum(f.stat().st_size for f in FIXTURES.rglob("*") if f.is_file())
    print(f"Total fixture size: {total / 1024:.1f} KB")


if __name__ == "__main__":
    main()
