import os
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import computed_field
from pydantic import model_validator
from typing import Any, Optional, Union, ClassVar
from uuid import UUID

import logging
from gemini.storage.providers.minio_storage import MinioStorageProvider
from gemini.storage.config.storage_config import MinioStorageConfig
from gemini.manager import GEMINIManager, GEMINIComponentType

from functools import cached_property
from abc import ABC, abstractmethod

manager = GEMINIManager()
minio_storage_settings = manager.get_component_settings(GEMINIComponentType.STORAGE)
minio_storage_config = MinioStorageConfig(
    endpoint=f"{minio_storage_settings['GEMINI_STORAGE_HOSTNAME']}:{minio_storage_settings['GEMINI_STORAGE_PORT']}",
    access_key=minio_storage_settings['GEMINI_STORAGE_ACCESS_KEY'],
    secret_key=minio_storage_settings['GEMINI_STORAGE_SECRET_KEY'],
    bucket_name=minio_storage_settings['GEMINI_STORAGE_BUCKET_NAME'],
    secure=False
)
minio_storage_provider = MinioStorageProvider(minio_storage_config)

logger = logging.getLogger(__name__)

class APIBase(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        protected_namespaces=(),
        extra="allow"
    )

    @classmethod
    @abstractmethod
    def exists(cls, **kwargs) -> bool:
        pass

    @classmethod
    @abstractmethod
    def create(cls, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def get_by_id(cls, id: Union[UUID, int, str]):
        pass

    @classmethod
    @abstractmethod
    def get_all(cls):
        pass

    @classmethod
    @abstractmethod
    def get(cls, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def search(cls, **search_parameters):
        pass

    @abstractmethod
    def update(self, **kwargs):
        pass

    @abstractmethod
    def delete(self):
        pass

    @abstractmethod
    def refresh(self):
        pass

class FileHandlerMixin(BaseModel):

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

    minio_storage_provider: ClassVar[MinioStorageProvider] = minio_storage_provider

    @classmethod
    @abstractmethod
    def process_record(cls, record: 'APIBase') -> 'APIBase':
        pass
    
    @classmethod
    @abstractmethod
    def create_file_uri(cls, record_file_key: str) -> str:
        pass

