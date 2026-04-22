# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GEMINI Framework is a Python back-end for the GEMINI Breeding project (UC Davis). It provides a data management pipeline for agricultural breeding research, encompassing sensor data, trait records, experiments, plots, cultivars, and more. The system runs as a set of Docker containers (PostgreSQL, Redis, MinIO, REST API, scheduler).

## Build & Run Commands

```bash
# Install dependencies (uses Poetry as build backend)
poetry install

# CLI commands (after install)
gemini setup --default   # First-time setup: writes .env and builds containers
gemini build             # Build Docker containers
gemini start             # Start pipeline (docker compose up)
gemini stop              # Stop pipeline
gemini clean             # Remove containers and images
gemini reset             # Save settings, rebuild from scratch

# Alternative via Taskfile (requires 'task' CLI)
task start               # Start containers
task stop                # Stop containers
task reset-containers    # Clean and restart

# Documentation
mkdocs serve             # Serve docs locally (mkdocs-material)
```

## Architecture

### Three-Layer Design

1. **`gemini/api/`** — Pydantic-based Python API. Each domain entity (Experiment, Sensor, Trait, Dataset, etc.) has a class extending `APIBase` (in `api/base.py`) with `create`, `get`, `get_all`, `exists` abstract methods. These are the public-facing Python classes users interact with.

2. **`gemini/db/`** — SQLAlchemy ORM layer targeting PostgreSQL (schema: `gemini`).
   - `db/core/base.py`: `BaseModel` (SQLAlchemy `DeclarativeBase`) with generic CRUD operations. All DB models inherit from this.
   - `db/core/engine.py`: `DatabaseEngine` manages sync + async engines/sessions with connection pooling.
   - `db/models/`: One file per entity table. `db/models/views/` contains materialized views (IMMV pattern) and regular views. `db/models/columnar/` holds time-series record tables.
   - `db/models/associations.py`: Many-to-many association tables.

3. **`gemini/rest_api/`** — Litestar-based REST API. `app.py` auto-registers controllers from `controllers/` dict. Each controller maps to a domain entity. API docs served via Stoplight plugin.

### Supporting Modules

- **`gemini/manager.py`**: `GEMINIManager` orchestrates Docker containers and settings. Used as an entry point by both CLI and API layers to get component connection settings.
- **`gemini/config/settings.py`**: `GEMINISettings` (pydantic-settings) loads config from `gemini/pipeline/.env`. Has `internal`/`public`/`local` deployment modes that remap hostnames.
- **`gemini/storage/`**: Pluggable storage layer with provider interface. Implementations: MinIO (primary), S3, local filesystem.
- **`gemini/logger/`**: Redis-backed logging.
- **`gemini/cli/`**: Click-based CLI (`__main__.py`). Entry point: `gemini.cli.__main__:cli`.
- **`gemini/pipeline/`**: Docker compose file and `.env` files for the container stack.

### Key Patterns

- DB connection settings are resolved at module import time in `db/core/base.py` and `api/base.py` via `GEMINIManager().get_component_settings(...)`. Changing DB config requires updating the `.env` file before import.
- API classes use Pydantic models with `from_attributes=True` to convert from SQLAlchemy ORM objects.
- The DB uses a `gemini` schema (not default `public`).
- Python 3.12 required (pinned `>=3.12, <3.13`).

## Testing

The project uses pytest with comprehensive import guards to mock infrastructure dependencies (Docker, MinIO, Redis, PostgreSQL) so tests run without any running services.

```bash
# Install test dependencies
uv pip install --python .venv/bin/python pytest pytest-cov pytest-asyncio pytest-mock pytest-xdist factory-boy pillow

# Run all unit tests
.venv/bin/python -m pytest tests/unit/ -v

# Run with coverage report
.venv/bin/python -m pytest tests/unit/ --cov=gemini --cov-report=term-missing

# Run in parallel
.venv/bin/python -m pytest tests/unit/ -n auto

# Run a specific layer
.venv/bin/python -m pytest tests/unit/api/ -v
.venv/bin/python -m pytest tests/unit/rest_api/ -v
.venv/bin/python -m pytest tests/unit/db/ -v
```

### Test Architecture

- **`tests/conftest.py`** — Root import guards. Patches `sys.modules` for `docker`, `minio`, `redis`, `boto3`, `botocore`, `asyncpg` before any `gemini.*` module is imported. Sets test environment variables. This is the keystone file — all tests depend on it.
- **`tests/unit/db/conftest.py`** — Auto-use fixture patching `gemini.db.core.base.db_engine` with a mock `DatabaseEngine`.
- **`tests/unit/rest_api/conftest.py`** — Litestar `TestClient` fixture.
- **`tests/unit/cli/`** — Uses Click's `CliRunner`.

### Key Testing Patterns

- **Import-time side effects**: `gemini/manager.py`, `gemini/db/core/base.py`, and `gemini/api/base.py` execute infrastructure code at import time. The root `conftest.py` must be loaded first (pytest handles this automatically).
- **Lazy imports in API entities**: Association methods use `from gemini.api.experiment import Experiment` inside method bodies. Patch the **source module** (`gemini.api.experiment.Experiment`), not the calling module (`gemini.api.site.Experiment`).
- **REST controller tests**: Return actual Pydantic output model instances (e.g., `SiteOutput(**data)`) from mocks, not `MagicMock` — Litestar validates response types.
- **Exception classes**: The root conftest provides real exception subclasses for `minio.error.S3Error`, `botocore.exceptions.ClientError`, and `redis.exceptions.*` so `except` clauses work correctly.

### Integration Tests

Integration tests run against real PostgreSQL, MinIO, and Redis via a test-specific Docker Compose stack.

```bash
# Start test containers (standard PostgreSQL 16, no custom extensions)
docker compose -f tests/docker-compose.test.yaml up -d

# Run integration tests
.venv/bin/python -m pytest tests/integration/ -v -m integration

# Stop and clean up
docker compose -f tests/docker-compose.test.yaml down -v
```

- **`tests/docker-compose.test.yaml`** — PostgreSQL on 15432, MinIO on 19000, Redis on 16379. Uses `tests/init_sql/01_init.sql` for schema setup (heap storage, no Hydra/pg_ivm).
- **`tests/integration/conftest.py`** — Session-scoped fixture waits for DB, overrides `db_engine` with real connection, truncates all tables between tests.
- Tests are automatically skipped if Docker is not running.

### Coverage

Configuration is in `pyproject.toml` under `[tool.coverage.*]`. Examples, pipeline, and init_sql directories are excluded. The `gemini/examples/` directory contains usage examples for the Python API (not tests).

## Commits

When you commit, don't sign it as written by Claude Model X.
