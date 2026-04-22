"""
Root conftest.py - Patches import-time side effects.

This MUST be loaded before any gemini module is imported.
Pytest loads conftest.py files top-down, so this runs first.

The GEMINI Framework has several modules that execute infrastructure-connecting
code at import time:
- gemini/manager.py: docker.from_env() as class default
- gemini/db/core/base.py: GEMINIManager().get_component_settings()
- gemini/api/base.py: GEMINIManager() + MinioStorageProvider() init
"""
import sys
import os
from unittest.mock import MagicMock
import pytest

# ============================================================
# PHASE 1: Patch Docker SDK before gemini.manager is imported
# ============================================================
import types as _types_docker
mock_docker_module = _types_docker.ModuleType("docker")
mock_docker_client = MagicMock()
mock_docker_client.containers.list.return_value = []
mock_docker_module.from_env = MagicMock(return_value=mock_docker_client)
mock_docker_module.DockerClient = type(mock_docker_client)

mock_docker_errors = _types_docker.ModuleType("docker.errors")
class _DockerException(Exception):
    pass
class _APIError(_DockerException):
    pass
class _NotFound(_DockerException):
    pass
mock_docker_errors.DockerException = _DockerException
mock_docker_errors.APIError = _APIError
mock_docker_errors.NotFound = _NotFound
mock_docker_module.errors = mock_docker_errors

sys.modules["docker"] = mock_docker_module
sys.modules["docker.errors"] = mock_docker_errors

# ============================================================
# PHASE 2: Set environment variables for GEMINISettings
# ============================================================
_test_env = {
    "GEMINI_DEBUG": "False",
    "GEMINI_TYPE": "local",
    "GEMINI_PUBLIC_DOMAIN": "",
    "GEMINI_PUBLIC_IP": "",
    "GEMINI_DB_HOSTNAME": "localhost",
    "GEMINI_DB_PORT": "5432",
    "GEMINI_DB_USER": "test_user",
    "GEMINI_DB_PASSWORD": "test_pass",
    "GEMINI_DB_NAME": "test_db",
    "GEMINI_STORAGE_HOSTNAME": "localhost",
    "GEMINI_STORAGE_PORT": "9000",
    "GEMINI_STORAGE_API_PORT": "9001",
    "GEMINI_STORAGE_ROOT_USER": "test_root",
    "GEMINI_STORAGE_ROOT_PASSWORD": "test_root_pass",
    "GEMINI_STORAGE_ACCESS_KEY": "test_key",
    "GEMINI_STORAGE_SECRET_KEY": "test_secret",
    "GEMINI_STORAGE_BUCKET_NAME": "test_bucket",
    "GEMINI_LOGGER_HOSTNAME": "localhost",
    "GEMINI_LOGGER_PORT": "6379",
    "GEMINI_LOGGER_PASSWORD": "test_pass",
    "GEMINI_REST_API_HOSTNAME": "localhost",
    "GEMINI_REST_API_PORT": "7777",
    "GEMINI_SCHEDULER_DB_HOSTNAME": "localhost",
    "GEMINI_SCHEDULER_DB_PORT": "6432",
    "GEMINI_SCHEDULER_DB_USER": "test_user",
    "GEMINI_SCHEDULER_DB_PASSWORD": "test_pass",
    "GEMINI_SCHEDULER_DB_NAME": "test_scheduler",
    "GEMINI_SCHEDULER_SERVER_HOSTNAME": "localhost",
    "GEMINI_SCHEDULER_SERVER_PORT": "4200",
}
for key, value in _test_env.items():
    os.environ.setdefault(key, value)

# ============================================================
# PHASE 3: Patch MinIO client before api/base.py is imported
# ============================================================
# Create a real S3Error exception class so isinstance() checks work
import types

mock_minio_module = types.ModuleType("minio")
mock_minio_module.Minio = MagicMock(return_value=MagicMock())

mock_minio_error = types.ModuleType("minio.error")

class _S3Error(Exception):
    def __init__(self, message="", resource="", request_id="", host_id="",
                 response="NoSuchKey", code="", bucket_name="", object_name=""):
        self.message = message
        super().__init__(message)

mock_minio_error.S3Error = _S3Error
mock_minio_module.error = mock_minio_error

sys.modules["minio"] = mock_minio_module
sys.modules["minio.error"] = mock_minio_error

# ============================================================
# PHASE 4: Patch redis before logger is imported
# ============================================================
mock_redis_module = types.ModuleType("redis")
mock_redis_module.Redis = MagicMock()  # A callable mock whose return_value can be set
mock_redis_module.StrictRedis = MagicMock()

# Create real redis exception classes
mock_redis_exceptions = types.ModuleType("redis.exceptions")

class _RedisConnectionError(Exception):
    pass

class _RedisAuthenticationError(Exception):
    pass

class _RedisError(Exception):
    pass

mock_redis_exceptions.ConnectionError = _RedisConnectionError
mock_redis_exceptions.AuthenticationError = _RedisAuthenticationError
mock_redis_exceptions.RedisError = _RedisError
mock_redis_module.exceptions = mock_redis_exceptions

# Also expose exceptions at top-level (redis.ConnectionError, redis.AuthenticationError)
# because the source code uses `except redis.ConnectionError` directly
mock_redis_module.ConnectionError = _RedisConnectionError
mock_redis_module.AuthenticationError = _RedisAuthenticationError
mock_redis_module.RedisError = _RedisError

sys.modules["redis"] = mock_redis_module
sys.modules["redis.exceptions"] = mock_redis_exceptions

# ============================================================
# PHASE 5: Patch boto3/botocore before s3_storage is imported
# ============================================================
mock_boto3_module = MagicMock()
sys.modules["boto3"] = mock_boto3_module

mock_botocore = types.ModuleType("botocore")
mock_botocore_config = types.ModuleType("botocore.config")
mock_botocore_config.Config = MagicMock

mock_botocore_exceptions = types.ModuleType("botocore.exceptions")

class _ClientError(Exception):
    def __init__(self, error_response=None, operation_name=""):
        # Support both dict-style (botocore real) and (code, message) style calls
        if isinstance(error_response, dict):
            self.response = error_response
        elif isinstance(error_response, str):
            # Called as _ClientError("404", "Not Found") by tests
            self.response = {"Error": {"Code": error_response, "Message": operation_name}}
        else:
            self.response = {"Error": {"Code": "Unknown", "Message": ""}}
        self.operation_name = operation_name if not isinstance(error_response, str) else ""
        code = self.response.get("Error", {}).get("Code", "")
        msg = self.response.get("Error", {}).get("Message", "")
        super().__init__(f"{code}: {msg}")

class _NoCredentialsError(Exception):
    pass

class _PartialCredentialsError(Exception):
    def __init__(self, provider="", cred_var=""):
        super().__init__(f"Partial credentials found in {provider}, missing: {cred_var}")

mock_botocore_exceptions.ClientError = _ClientError
mock_botocore_exceptions.NoCredentialsError = _NoCredentialsError
mock_botocore_exceptions.PartialCredentialsError = _PartialCredentialsError
mock_botocore.exceptions = mock_botocore_exceptions
mock_botocore.config = mock_botocore_config

sys.modules["botocore"] = mock_botocore
sys.modules["botocore.config"] = mock_botocore_config
sys.modules["botocore.exceptions"] = mock_botocore_exceptions

# ============================================================
# PHASE 6: Patch asyncpg to avoid connection attempts
# ============================================================
mock_asyncpg = MagicMock()
sys.modules["asyncpg"] = mock_asyncpg

# ============================================================
# Shared fixtures
# ============================================================

@pytest.fixture
def mock_docker_client_fixture():
    """Provides the pre-patched mock Docker client."""
    return mock_docker_client


@pytest.fixture
def test_settings():
    """Provides a GEMINISettings instance with test defaults."""
    from gemini.config.settings import GEMINISettings
    return GEMINISettings()


@pytest.fixture
def mock_manager():
    """Provides a GEMINIManager with mocked Docker."""
    from gemini.manager import GEMINIManager
    manager = GEMINIManager()
    return manager
