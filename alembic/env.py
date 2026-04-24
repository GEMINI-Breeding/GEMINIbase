"""
Alembic environment configuration for GEMINIbase.

Reads the database URL from environment variables (same as the application)
and uses the GEMINIbase BaseModel metadata for autogenerate support.
"""
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Alembic Config object
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Build database URL from environment variables (same vars used by the app)
# Prefer GEMINI_DB_URL (passed into the rest-api container) and fall back to
# the individual GEMINI_DB_* vars (used by local dev/pytest against a
# published port on the host).
database_url = os.environ.get("GEMINI_DB_URL")
if not database_url:
    db_user = os.environ.get("GEMINI_DB_USER", "gemini")
    db_pass = os.environ.get("GEMINI_DB_PASSWORD", "gemini")
    db_host = os.environ.get("GEMINI_DB_HOSTNAME", "localhost")
    db_port = os.environ.get("GEMINI_DB_PORT", "5432")
    db_name = os.environ.get("GEMINI_DB_NAME", "gemini")
    database_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

# Override the sqlalchemy.url from alembic.ini with the env-based URL
config.set_main_option("sqlalchemy.url", database_url)

# Import all models so Alembic can detect them for autogenerate.
# The metadata object comes from BaseModel which uses schema="gemini".
from gemini.db.core.base import BaseModel  # noqa: E402
# Import all model modules to register them with the metadata
import gemini.db.models  # noqa: E402, F401

target_metadata = BaseModel.metadata


def include_name(name, type_, parent_names):
    """Only include objects in the 'gemini' schema."""
    if type_ == "schema":
        return name == "gemini"
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection needed)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_name=include_name,
        version_table_schema="gemini",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (requires DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
            version_table_schema="gemini",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
