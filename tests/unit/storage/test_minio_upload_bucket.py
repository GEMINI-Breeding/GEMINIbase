"""MinioStorageProvider uploads/URLs for buckets other than the default one,
and which upload errors are worth retrying."""
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from gemini.storage.config.storage_config import MinioStorageConfig
from gemini.storage.exceptions import StorageError, StorageUploadError
from gemini.storage.providers.minio_storage import MinioStorageProvider
from minio.error import S3Error

DEFAULT_BUCKET = "test-bucket"
OTHER_BUCKET = "other-bucket"


@pytest.fixture
def provider():
    provider = MinioStorageProvider(MinioStorageConfig(
        endpoint="localhost:9000", access_key="k", secret_key="s",
        bucket_name=DEFAULT_BUCKET, secure=False,
    ))
    provider.client = MagicMock()

    def stat_object(bucket_name, object_name):
        # The object only exists in the bucket it was uploaded to.
        if bucket_name != OTHER_BUCKET:
            raise S3Error("NoSuchKey", "not found")
        return MagicMock()

    provider.client.stat_object.side_effect = stat_object
    provider.client.presigned_get_object.return_value = "https://signed"
    return provider


@pytest.fixture
def no_sleep():
    with patch("gemini.storage.providers.minio_storage.time.sleep") as sleep:
        yield sleep


def test_upload_to_other_bucket_succeeds_first_time(provider, no_sleep, tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("x")
    url = provider.upload_file(object_name="a.txt", input_file_path=src, bucket_name=OTHER_BUCKET)
    assert url == "https://signed"
    provider.client.fput_object.assert_called_once()
    no_sleep.assert_not_called()


def test_download_url_checks_the_requested_bucket(provider):
    assert provider.get_download_url("a.txt", bucket_name=OTHER_BUCKET) == "https://signed"


def test_url_failure_after_upload_does_not_reupload(provider, no_sleep, tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("x")
    provider.client.presigned_get_object.side_effect = S3Error("InternalError", "boom")
    with pytest.raises(StorageError):
        provider.upload_file(object_name="a.txt", input_file_path=src, bucket_name=OTHER_BUCKET)
    provider.client.fput_object.assert_called_once()
    no_sleep.assert_not_called()


def test_missing_input_file_is_not_retried(provider, no_sleep, tmp_path):
    with pytest.raises(StorageUploadError):
        provider.upload_file(object_name="a.txt", input_file_path=tmp_path / "missing.txt")
    no_sleep.assert_not_called()


def test_missing_input_is_not_retried(provider, no_sleep):
    with pytest.raises(ValueError):
        provider.upload_file(object_name="a.txt")
    no_sleep.assert_not_called()

