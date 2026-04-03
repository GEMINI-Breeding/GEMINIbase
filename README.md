# GEMINI Backend Database Framework

![GEMINI Logo](docs/assets/logo_large.png "GEMINI Project")

Back-end data management framework for the [GEMINI Breeding project](https://projectgemini.ucdavis.edu/) (UC Davis). Manages field phenotyping data — sensor imagery, trait measurements, genomics, weather — across experiments, sites, seasons, plots, and cultivars.

## Requirements

- **Python 3.12**
- **Docker Desktop** ([download](https://www.docker.com/products/docker-desktop/))

## Quick Start

```bash
git clone https://github.com/GEMINI-Breeding/gemini-framework.git
cd gemini-framework

python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

### Run tests

```bash
# Unit tests (no Docker needed)
pytest tests/unit/ -v

# Integration tests (requires Docker)
docker compose -f tests/docker-compose.test.yaml up -d
pytest tests/integration/ -v
docker compose -f tests/docker-compose.test.yaml down -v
```

See [Testing documentation](docs/testing.md) for details.

### Run the full pipeline

```bash
gemini setup --default   # First-time setup
gemini build             # Build Docker containers
gemini start             # Start pipeline

# REST API at http://localhost:7777
```

## Architecture

Three-layer design:

1. **`gemini/api/`** — Pydantic-based Python API with CRUD operations for each domain entity
2. **`gemini/db/`** — SQLAlchemy ORM layer targeting PostgreSQL
3. **`gemini/rest_api/`** — Litestar REST API with 19 controllers

Supporting modules: storage (MinIO/S3/local), logging (Redis), CLI (Click), configuration (pydantic-settings).

## Documentation

```bash
mkdocs serve    # http://localhost:8000
```
