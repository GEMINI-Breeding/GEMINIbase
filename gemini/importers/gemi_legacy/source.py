"""Where the old install is visible to this container.

Compose mounts the old app's folder (holding gemi.db) and its data folder
read-only at these paths when there is one to import; otherwise they are
empty volumes. The API reads them to plan (the dry run), the geo worker to
copy.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

APP_DIR_ENV = "GEMINI_LEGACY_APP_DIR"
DATA_DIR_ENV = "GEMINI_LEGACY_DATA_DIR"


def legacy_app_dir() -> Path:
    return Path(os.environ.get(APP_DIR_ENV, "/legacy/app"))


def legacy_data_dir() -> Path:
    return Path(os.environ.get(DATA_DIR_ENV, "/legacy/data"))


def legacy_database() -> Optional[Path]:
    """gemi.db if an old install is mounted, else None."""
    db = legacy_app_dir() / "gemi.db"
    return db if db.is_file() and db.stat().st_size > 0 else None
