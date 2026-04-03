"""Tests for gemini.api.base module - APIBase and FileHandlerMixin."""
import pytest
from unittest.mock import MagicMock, patch
from abc import ABC

from gemini.api.base import APIBase, FileHandlerMixin


class TestAPIBase:
    """Tests for the APIBase abstract class."""

    def test_apibase_is_abstract(self):
        """Verify APIBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            APIBase()

    def test_apibase_has_abstract_methods(self):
        """Verify all expected abstract methods are declared."""
        abstract_methods = APIBase.__abstractmethods__
        expected = {"exists", "create", "get_by_id", "get_all", "get", "search", "update", "delete", "refresh"}
        assert expected.issubset(abstract_methods)

    def test_apibase_model_config(self):
        """Verify model_config is set correctly."""
        config = APIBase.model_config
        assert config.get("from_attributes") is True
        assert config.get("arbitrary_types_allowed") is True
        assert config.get("extra") == "allow"

    def test_concrete_subclass_can_be_created(self):
        """Verify a concrete subclass with all abstract methods can be instantiated."""

        class ConcreteAPI(APIBase):
            name: str = "test"

            @classmethod
            def exists(cls, **kwargs):
                return True

            @classmethod
            def create(cls, **kwargs):
                return cls()

            @classmethod
            def get_by_id(cls, id):
                return cls()

            @classmethod
            def get_all(cls):
                return []

            @classmethod
            def get(cls, **kwargs):
                return cls()

            @classmethod
            def search(cls, **search_parameters):
                return []

            def update(self, **kwargs):
                return self

            def delete(self):
                return True

            def refresh(self):
                return self

        instance = ConcreteAPI()
        assert instance.name == "test"
        assert instance.exists() is True


class TestFileHandlerMixin:
    """Tests for the FileHandlerMixin."""

    def test_file_handler_mixin_has_abstract_methods(self):
        """Verify FileHandlerMixin declares abstract methods."""
        abstract_methods = FileHandlerMixin.__abstractmethods__
        assert "process_record" in abstract_methods
        assert "create_file_uri" in abstract_methods

    def test_file_handler_mixin_has_storage_provider(self):
        """Verify FileHandlerMixin has a minio_storage_provider ClassVar."""
        assert hasattr(FileHandlerMixin, "minio_storage_provider")

    def test_file_handler_mixin_model_config(self):
        """Verify FileHandlerMixin model_config allows arbitrary types."""
        config = FileHandlerMixin.model_config
        assert config.get("arbitrary_types_allowed") is True
