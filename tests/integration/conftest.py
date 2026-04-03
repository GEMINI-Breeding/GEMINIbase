"""
Integration test fixtures.

These tests require the test Docker stack to be running:
    docker compose -f tests/docker-compose.test.yaml up -d

The root conftest.py already patches Docker/Minio/Redis at import time.
We override the DB engine here to point at the real test PostgreSQL.
"""
import os
import pytest
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Test DB configuration (matches docker-compose.test.yaml)
TEST_DB_USER = "gemini_test"
TEST_DB_PASSWORD = "gemini_test"
TEST_DB_HOST = os.environ.get("GEMINI_TEST_DB_HOST", "localhost")
TEST_DB_PORT = os.environ.get("GEMINI_TEST_DB_PORT", "15432")
TEST_DB_NAME = "gemini_test"
TEST_DB_URL = f"postgresql://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"

# MinIO test configuration
TEST_MINIO_HOST = os.environ.get("GEMINI_TEST_STORAGE_HOST", "localhost")
TEST_MINIO_PORT = os.environ.get("GEMINI_TEST_STORAGE_PORT", "19000")

# Redis test configuration
TEST_REDIS_HOST = os.environ.get("GEMINI_TEST_LOGGER_HOST", "localhost")
TEST_REDIS_PORT = os.environ.get("GEMINI_TEST_LOGGER_PORT", "16379")


def _wait_for_db(url: str, timeout: int = 30) -> bool:
    """Wait for the test database to be ready."""
    engine = create_engine(url)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return True
        except Exception:
            time.sleep(1)
    engine.dispose()
    return False


@pytest.fixture(scope="session", autouse=True)
def ensure_test_db():
    """Session-scoped fixture: verify the test DB is up and has the gemini schema."""
    if not _wait_for_db(TEST_DB_URL, timeout=30):
        pytest.skip(
            "Test database not available. Start it with:\n"
            "  docker compose -f tests/docker-compose.test.yaml up -d"
        )

    # Verify the gemini schema exists
    engine = create_engine(TEST_DB_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'gemini'")
        )
        if result.scalar() is None:
            engine.dispose()
            pytest.skip("Test database does not have 'gemini' schema. Check init_sql volume mount.")

    engine.dispose()
    yield


@pytest.fixture(scope="module")
def db_engine():
    """Provide a real SQLAlchemy engine connected to the test DB."""
    from gemini.db.core.engine import DatabaseEngine
    from gemini.db.config import DatabaseConfig

    config = DatabaseConfig(database_url=TEST_DB_URL)
    engine = DatabaseEngine(config)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def setup_real_db(db_engine):
    """
    Override the global db_engine in gemini.db.core.base so all model operations
    hit the real test database instead of the mock.

    Module-scoped so the real engine is restored before unit tests run.
    """
    from gemini.db.core import base as base_module
    original_engine = base_module.db_engine
    base_module.db_engine = db_engine
    yield db_engine
    base_module.db_engine = original_engine


@pytest.fixture(autouse=True)
def clean_db(setup_real_db):
    """
    Function-scoped fixture: truncate all gemini tables before each test.
    This ensures test isolation without rebuilding the schema.
    """
    engine = setup_real_db
    # Tables to truncate between tests. Excludes reference/seed tables
    # (data_types, data_formats, sensor_types, trait_levels, dataset_types,
    #  data_type_formats) since they contain seed data that FK defaults depend on.
    tables = [
        "gemini.sensor_records", "gemini.trait_records", "gemini.dataset_records",
        "gemini.model_records", "gemini.procedure_records", "gemini.script_records",
        "gemini.plot_cultivars", "gemini.plants",
        "gemini.sensor_platform_sensors", "gemini.sensor_datasets",
        "gemini.trait_datasets", "gemini.trait_sensors",
        "gemini.model_datasets", "gemini.script_datasets", "gemini.procedure_datasets",
        "gemini.experiment_sites", "gemini.experiment_sensors",
        "gemini.experiment_sensor_platforms", "gemini.experiment_traits",
        "gemini.experiment_cultivars", "gemini.experiment_datasets",
        "gemini.experiment_models", "gemini.experiment_procedures",
        "gemini.experiment_scripts",
        "gemini.script_runs", "gemini.model_runs", "gemini.procedure_runs",
        "gemini.plots", "gemini.seasons",
        "gemini.sensors", "gemini.sensor_platforms",
        "gemini.scripts", "gemini.models", "gemini.procedures",
        "gemini.datasets", "gemini.traits", "gemini.cultivars",
        "gemini.resources",
        "gemini.experiments", "gemini.sites",
    ]
    with engine.get_session() as session:
        for table in tables:
            session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
    yield
