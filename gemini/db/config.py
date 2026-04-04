"""
Configuration for the database connection.
"""

import os
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.pool import QueuePool, AsyncAdaptedQueuePool

class DatabaseConfig(BaseModel):
    """
    Database configuration settings.

    Features:
    - Environment variable-based configuration
    - Validation and parsing of database URLs
    - Support for both sync and async database URLs
    - Configurable connection pool settings
    """

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800
    echo_sql: bool = False
    echo_pool: bool = False
    pool_class: type = QueuePool
    isolation_level: str = "READ COMMITTED"
    async_pool_class: type = AsyncAdaptedQueuePool

    @field_validator("database_url", mode="before")
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("Database URL must be provided")
        return v
