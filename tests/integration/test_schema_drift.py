"""ORM ↔ live-DB schema drift check.

Catches the class of bug that produced the silent
``column experiment_files.metadata_json does not exist`` failures: a
column declared on a SQLAlchemy model whose corresponding ALTER /
CREATE never made it into ``init_sql`` (or whose Alembic migration
never ran).

For every table currently registered in ``BaseModel.metadata`` that
also exists in the live DB, assert that every ORM-declared column is
present. Tables intentionally absent from the test schema (e.g.
columnar/IMMV tables on the minimalist test DB) are skipped — only
real drift on tables that *do* exist is reported.

By default this runs against the test docker-compose DB on port 15432.
Point at the live dev DB with::

    GEMINI_TEST_DB_HOST=localhost GEMINI_TEST_DB_PORT=5432 \
        GEMINI_TEST_DB_USER=gemini GEMINI_TEST_DB_PASSWORD=gemini \
        GEMINI_TEST_DB_NAME=gemini \
        pytest tests/integration/test_schema_drift.py -v
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration


def _build_db_url() -> str:
    user = os.environ.get("GEMINI_TEST_DB_USER", "gemini_test")
    password = os.environ.get("GEMINI_TEST_DB_PASSWORD", "gemini_test")
    host = os.environ.get("GEMINI_TEST_DB_HOST", "localhost")
    port = os.environ.get("GEMINI_TEST_DB_PORT", "15432")
    name = os.environ.get("GEMINI_TEST_DB_NAME", "gemini_test")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def test_orm_columns_exist_in_live_db():
    # Importing the package registers every ORM model with
    # ``BaseModel.metadata`` so we can enumerate them below.
    import gemini.db.models  # noqa: F401
    from gemini.db.core.base import BaseModel

    engine = create_engine(_build_db_url())
    try:
        with engine.connect() as conn:
            db_tables = {
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'gemini'"
                    )
                )
            }
            db_columns: dict[str, set[str]] = {}
            for table in db_tables:
                db_columns[table] = {
                    row[0]
                    for row in conn.execute(
                        text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_schema = 'gemini' AND table_name = :t"
                        ),
                        {"t": table},
                    )
                }
    finally:
        engine.dispose()

    drift: list[str] = []
    checked_tables = 0
    for table in BaseModel.metadata.tables.values():
        # MetaData was created with ``schema='gemini'``; .name is the
        # bare table name (no schema prefix).
        name = table.name
        if name not in db_tables:
            # Intentionally absent in this DB (e.g., columnar/IMMV
            # tables on the test schema). Not drift — skip.
            continue
        checked_tables += 1
        declared = {col.name for col in table.columns}
        actual = db_columns[name]
        missing = declared - actual
        if missing:
            drift.append(
                f"{name}: ORM declares {sorted(declared)} but DB is "
                f"missing {sorted(missing)}"
            )

    assert checked_tables > 0, (
        "no ORM tables matched any DB tables — fixture wiring problem"
    )
    assert not drift, "ORM ↔ DB schema drift detected:\n  " + "\n  ".join(drift)


def test_experiment_files_has_metadata_json():
    """Targeted regression test for the specific bug that motivated the
    broader drift check above. Cheap, runs even against a stripped-down
    test DB, and gives a focused failure message when this column goes
    missing again."""
    engine = create_engine(_build_db_url())
    try:
        with engine.connect() as conn:
            cols = {
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'gemini' "
                        "AND table_name = 'experiment_files'"
                    )
                )
            }
    finally:
        engine.dispose()

    if not cols:
        pytest.skip(
            "experiment_files table is not present in this DB — add it to "
            "tests/init_sql/01_init.sql to enable this regression check."
        )
    assert "metadata_json" in cols, (
        "experiment_files is missing the metadata_json JSONB column. "
        "Image Exclusion + GCP picker rely on this column being present "
        "and writable. Re-run init_sql or apply migration "
        "alembic/versions/0005_experiment_files_metadata.py."
    )
