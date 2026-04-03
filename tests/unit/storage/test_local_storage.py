"""Tests for LocalStorageProvider."""

import io
import json
import pytest
from pathlib import Path

from gemini.storage.providers.local_storage import LocalStorageProvider
from gemini.storage.config.storage_config import LocalStorageConfig
from gemini.storage.exceptions import (
    StorageError,
    StorageFileNotFoundError,
    StorageInitializationError,
    StorageUploadError,
)


@pytest.fixture
def local_config(tmp_path):
    """Create a LocalStorageConfig pointing at a tmp directory."""
    return LocalStorageConfig(
        root_directory=tmp_path / "storage",
        create_directory=True,
    )


@pytest.fixture
def provider(local_config):
    """Create a LocalStorageProvider with a temporary root directory."""
    return LocalStorageProvider(local_config)


# ── __init__ ──────────────────────────────────────────────────────


class TestInit:
    def test_creates_directory_when_create_directory_true(self, tmp_path):
        target = tmp_path / "new_dir"
        assert not target.exists()
        config = LocalStorageConfig(root_directory=target, create_directory=True)
        LocalStorageProvider(config)
        assert target.exists()

    def test_raises_when_directory_missing_and_create_false(self, tmp_path):
        target = tmp_path / "nonexistent"
        config = LocalStorageConfig(
            root_directory=target, create_directory=False
        )
        with pytest.raises(StorageInitializationError, match="does not exist"):
            LocalStorageProvider(config)

    def test_succeeds_when_directory_exists_and_create_false(self, tmp_path):
        target = tmp_path / "existing"
        target.mkdir()
        config = LocalStorageConfig(
            root_directory=target, create_directory=False
        )
        prov = LocalStorageProvider(config)
        assert prov.root_directory == target.resolve()


# ── initialize ────────────────────────────────────────────────────


class TestInitialize:
    def test_creates_directory(self, tmp_path):
        target = tmp_path / "init_dir"
        config = LocalStorageConfig(root_directory=target, create_directory=True)
        prov = LocalStorageProvider(config)
        # Remove the directory that __init__ created
        target.rmdir()
        assert not target.exists()
        result = prov.initialize()
        assert result is True
        assert target.exists()


# ── upload_file ───────────────────────────────────────────────────


class TestUploadFile:
    def test_writes_file_and_returns_url(self, provider):
        data = io.BytesIO(b"hello world")
        url = provider.upload_file("test.txt", data, content_type="text/plain")
        assert url.startswith("file://")
        written = (provider.root_directory / "test.txt").read_bytes()
        assert written == b"hello world"

    def test_stores_metadata(self, provider):
        data = io.BytesIO(b"data")
        provider.upload_file(
            "meta.txt",
            data,
            content_type="text/plain",
            metadata={"author": "test"},
        )
        meta_path = provider.root_directory / "meta.txt.meta"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["content_type"] == "text/plain"
        assert meta["author"] == "test"

    def test_creates_subdirectories(self, provider):
        data = io.BytesIO(b"nested")
        url = provider.upload_file("a/b/c.txt", data)
        assert (provider.root_directory / "a" / "b" / "c.txt").exists()


# ── download_file ─────────────────────────────────────────────────


class TestDownloadFile:
    def test_copies_file_to_destination(self, provider, tmp_path):
        # Upload a file first
        (provider.root_directory / "src.txt").write_bytes(b"content")
        dest = tmp_path / "dest" / "copy.txt"
        result = provider.download_file("src.txt", dest)
        assert result == dest
        assert dest.read_bytes() == b"content"

    def test_raises_for_missing_file(self, provider, tmp_path):
        dest = tmp_path / "out.txt"
        with pytest.raises(StorageFileNotFoundError, match="File not found"):
            provider.download_file("nope.txt", dest)


# ── delete_file ───────────────────────────────────────────────────


class TestDeleteFile:
    def test_removes_file_and_meta(self, provider):
        fp = provider.root_directory / "del.txt"
        fp.write_bytes(b"bye")
        meta = fp.with_suffix(".txt.meta")
        meta.write_text("{}")
        assert provider.delete_file("del.txt") is True
        assert not fp.exists()
        assert not meta.exists()

    def test_returns_false_for_missing_file(self, provider):
        assert provider.delete_file("missing.txt") is False


# ── get_download_url ──────────────────────────────────────────────


class TestGetDownloadUrl:
    def test_returns_file_url(self, provider):
        fp = provider.root_directory / "url.txt"
        fp.write_bytes(b"x")
        url = provider.get_download_url("url.txt")
        assert url == f"file://{fp.absolute()}"

    def test_raises_for_missing_file(self, provider):
        with pytest.raises(StorageFileNotFoundError):
            provider.get_download_url("nope.txt")


# ── list_files ────────────────────────────────────────────────────


class TestListFiles:
    def test_lists_files(self, provider):
        (provider.root_directory / "a.txt").write_bytes(b"")
        (provider.root_directory / "b.txt").write_bytes(b"")
        files = provider.list_files()
        assert "a.txt" in files
        assert "b.txt" in files

    def test_filters_meta_files(self, provider):
        (provider.root_directory / "data.txt").write_bytes(b"")
        (provider.root_directory / "data.txt.meta").write_text("{}")
        files = provider.list_files()
        assert "data.txt" in files
        assert "data.txt.meta" not in files

    def test_prefix_filter(self, provider):
        sub = provider.root_directory / "sub"
        sub.mkdir()
        (sub / "in.txt").write_bytes(b"")
        (provider.root_directory / "out.txt").write_bytes(b"")
        files = provider.list_files(prefix="sub")
        assert any("in.txt" in f for f in files)
        assert not any("out.txt" in f for f in files)

    def test_recursive_false(self, provider):
        sub = provider.root_directory / "deep"
        sub.mkdir()
        (sub / "nested.txt").write_bytes(b"")
        (provider.root_directory / "top.txt").write_bytes(b"")
        files = provider.list_files(recursive=False)
        assert "top.txt" in files
        # Non-recursive glob("*") won't pick up nested files
        assert not any("nested.txt" in f for f in files)


# ── file_exists ───────────────────────────────────────────────────


class TestFileExists:
    def test_true_when_exists(self, provider):
        (provider.root_directory / "yes.txt").write_bytes(b"")
        assert provider.file_exists("yes.txt") is True

    def test_false_when_missing(self, provider):
        assert provider.file_exists("no.txt") is False


# ── get_file_metadata ─────────────────────────────────────────────


class TestGetFileMetadata:
    def test_returns_metadata(self, provider):
        fp = provider.root_directory / "info.txt"
        fp.write_bytes(b"12345")
        meta = provider.get_file_metadata("info.txt")
        assert meta["size"] == 5
        assert "created" in meta
        assert "modified" in meta
        assert "content_type" in meta
        assert isinstance(meta["metadata"], dict)

    def test_returns_custom_metadata(self, provider):
        fp = provider.root_directory / "custom.txt"
        fp.write_bytes(b"x")
        # Write companion metadata
        provider._save_metadata(fp, {"key": "val"})
        meta = provider.get_file_metadata("custom.txt")
        assert meta["metadata"]["key"] == "val"

    def test_raises_for_missing_file(self, provider):
        with pytest.raises(StorageFileNotFoundError):
            provider.get_file_metadata("nope.txt")


# ── _get_full_path (directory traversal) ──────────────────────────


class TestGetFullPath:
    def test_prevents_directory_traversal(self, provider):
        with pytest.raises(StorageError, match="outside root directory"):
            provider._get_full_path("../../etc/passwd")

    def test_normal_path_works(self, provider):
        path = provider._get_full_path("a/b.txt")
        assert str(path).startswith(str(provider.root_directory))
