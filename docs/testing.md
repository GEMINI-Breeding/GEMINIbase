# Testing

GEMINIbase has two test suites: **unit tests** that run without any infrastructure, and **integration tests** that run against real PostgreSQL, MinIO, and Redis via Docker.

## Running Tests

### Unit tests (no Docker needed)

```bash
pytest tests/unit/ -v
```

Unit tests mock all infrastructure dependencies (Docker, PostgreSQL, MinIO, Redis) so they validate Python logic, wiring, and argument passing without any running services.

### Integration tests (requires Docker)

```bash
# Start the test containers
docker compose -f tests/docker-compose.test.yaml up -d

# Run integration tests
pytest tests/integration/ -v

# Clean up when done
docker compose -f tests/docker-compose.test.yaml down -v
```

Integration tests hit a real database. They verify SQL correctness, constraint enforcement, cascade deletes, JSONB queries, bulk operations, REST endpoint behavior, and the full request cycle end-to-end.

If Docker is not running, integration tests skip automatically.

### Run everything

```bash
pytest tests/ -v
```

### Other useful commands

```bash
# Coverage report
pytest tests/unit/ --cov=gemini --cov-report=term-missing

# Run in parallel
pytest tests/unit/ -n auto

# Single test file
pytest tests/integration/test_records.py -v

# Single test
pytest tests/integration/test_db_crud.py::TestExperimentCRUD::test_create_experiment -v
```

## Test Infrastructure

### Integration test Docker stack

`tests/docker-compose.test.yaml` runs lightweight containers on offset ports to avoid conflicting with a development stack:

| Service | Image | Port | Credentials |
|---------|-------|------|-------------|
| PostgreSQL 16 | `postgres:16` | 15432 | `gemini_test` / `gemini_test` |
| MinIO | `minio/minio:latest` | 19000 (API), 19001 (console) | `minioadmin` / `minioadmin` |
| Redis | `redis:7-alpine` | 16379 | password: `gemini_test` |

The PostgreSQL instance uses **standard heap storage** (no Hydra columnar or pg_ivm extensions). Schema is initialized from `tests/init_sql/01_init.sql`, which creates all tables, association tables, record tables, and seeds reference data (data types, formats, sensor types, trait levels, dataset types).

### Test isolation

Each integration test gets a clean database. The `clean_db` fixture truncates all user-data tables between tests while preserving seeded reference data (data_types, data_formats, sensor_types, trait_levels, dataset_types).

### Unit test mocking

The root `tests/conftest.py` patches `sys.modules` before any `gemini.*` module is imported:

- `docker` — mocked so `GEMINIManager` doesn't scan real containers
- `minio` — mocked so `MinioStorageProvider` doesn't connect
- `redis` — mocked so logger doesn't connect
- `boto3` / `botocore` — mocked for S3 storage provider
- `asyncpg` — mocked to prevent async connection attempts

Environment variables are set to test defaults (localhost, test credentials).

`tests/unit/db/conftest.py` replaces the global `db_engine` with a mock that provides a fake session context manager, so all DB operations go to `MagicMock` instead of PostgreSQL.

## What the tests cover

### Integration tests

| Area | What is tested |
|------|---------------|
| **Entity CRUD** | Create, read, update, delete, search, exists, count for all entity types (Experiment, Site, Season, Population, Plot, Plant, Sensor, Trait, Dataset, Model, Script, Procedure, and their runs) |
| **Associations** | All 18 association table types — create, exists, cascade delete |
| **Record tables** | Insert, bulk insert, search, stream, pagination for all 6 record types (sensor, trait, dataset, model, procedure, script) |
| **REST API** | CRUD endpoints for all 18 controllers, pagination, search, seed data verification, error responses |
| **BaseModel methods** | update_bulk (upsert), get_or_update, update_or_create, paginate, JSONB contains search, count, update_parameter |

### Unit tests

Cover the Python API layer, DB model definitions, REST controller routing, storage providers (MinIO, S3, local), logger providers (Redis, local), CLI commands, configuration, and manager.

## Adding new tests

- **Unit tests** go in `tests/unit/` under the corresponding subdirectory (e.g., `tests/unit/api/`, `tests/unit/rest_api/controllers/`).
- **Integration tests** go in `tests/integration/`. Use the `setup_real_db` fixture to get a real database connection. Mark tests with `pytestmark = pytest.mark.integration`.
- If you add a new table, add it to the truncation list in `tests/integration/conftest.py` and to `tests/init_sql/01_init.sql`.
