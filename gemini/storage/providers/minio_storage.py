# gemini/storage/providers/minio_storage.py

import os
import sys
import time # Import time for sleep
from datetime import datetime, timedelta
from typing import BinaryIO, Optional, Union, Dict, Any
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from urllib3.response import HTTPResponse

from gemini.storage.interfaces.storage_provider import StorageProvider
from gemini.storage.config.storage_config import MinioStorageConfig
from gemini.storage.exceptions import (
    StorageError,
    StorageFileNotFoundError,
    StorageUploadError,
    StorageDownloadError,
    StorageDeleteError,
    StorageInitializationError,
    StorageConnectionError,
    StorageAuthError
)


class MinioStorageProvider(StorageProvider):
    """Provider for MinIO object storage."""

    def __init__(self, config: MinioStorageConfig):
        """Initialize MinIO client with configuration.
        
        Args:
            config: MinIO configuration
            
        Raises:
            StorageInitializationError: If client initialization fails
        """
        self.config = config
        try:
            self.client = Minio(
                endpoint=config.endpoint,
                access_key=config.access_key,
                secret_key=config.secret_key,
                secure=config.secure,
                region=config.region,
                http_client=config.http_client
            )
            self.bucket_name = config.bucket_name
        except Exception as e:
            raise StorageInitializationError(f"Failed to initialize MinIO client: {e}")

    def initialize(self) -> bool:
        """Initialize MinIO storage and create bucket if needed.
        
        Returns:
            bool: True if initialization successful
            
        Raises:
            StorageInitializationError: If initialization fails
        """
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name, self.config.region)
            return True
        except S3Error as e:
            raise StorageInitializationError(f"Failed to initialize MinIO storage: {e}")
        except Exception as e:
            raise StorageInitializationError(f"Unexpected error during initialization: {e}")

    def upload_file(
        self,
        object_name: str,
        data_stream: Optional[BinaryIO] = None,
        input_file_path: Optional[Union[str, Path]] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        bucket_name: Optional[str] = None
    ) -> str:
        """Upload a file to MinIO storage.
        
        Args:
            object_name: Name/path of the object in storage
            data_stream: File-like object containing the data
            content_type: MIME type of the file
            metadata: Additional metadata to store
            
        Returns:
            str: URL for the uploaded file
            
        Raises:
            StorageUploadError: If upload fails
            StorageConnectionError: If connection fails
            StorageAuthError: If access is denied after retries
        """
        max_retries = 5
        base_delay = 1.0 # seconds

        for attempt in range(max_retries):
            try:
                target_bucket_name = bucket_name if bucket_name is not None else self.bucket_name
                tags = metadata.copy() if metadata else {}
                if content_type:
                    tags['Content-Type'] = content_type
                
                # Note: part_size was removed in the base file content, keeping it removed here.
                # part_size = 5 * 1024 * 1024 # 5MB part size

                if input_file_path:
                    input_file_path = Path(input_file_path)
                    if not input_file_path.is_file():
                         raise FileNotFoundError(f"Input file path not found: {input_file_path}")
                    self.client.fput_object(
                        bucket_name=target_bucket_name,
                        object_name=object_name,
                        file_path=str(input_file_path),
                        content_type=content_type,
                        metadata=tags,
                        # part_size=part_size # Removed based on base file
                    )
                elif data_stream:
                    # Ensure stream is at the beginning before each attempt
                    current_pos = data_stream.tell()
                    data_stream.seek(0)
                    # Get file size - necessary for put_object
                    data_stream.seek(0, os.SEEK_END)
                    file_size = data_stream.tell()
                    data_stream.seek(0) # Reset stream position for upload

                    self.client.put_object(
                        bucket_name=target_bucket_name,
                        object_name=object_name,
                        data=data_stream,
                        length=file_size, # MinIO requires length for streams
                        content_type=content_type,
                        metadata=tags,
                        # part_size=part_size # Removed based on base file
                    )
                    # Restore original stream position if needed after successful upload?
                    # data_stream.seek(current_pos) # Maybe not necessary depending on caller
                else:
                     raise ValueError("Either data_stream or input_file_path must be provided")

                # If successful, get URL and return
                return self.get_download_url(object_name, bucket_name=target_bucket_name)

            except Exception as e: # Catch any exception for retry
                if attempt == max_retries - 1: # Last attempt failed
                    # Raise the specific storage exception based on e
                    if isinstance(e, S3Error) and 'AccessDenied' in str(e):
                         raise StorageAuthError(f"Access denied after {max_retries} attempts: {e}")
                    elif isinstance(e, ConnectionError): # Catch direct ConnectionError if it occurs outside S3Error
                         raise StorageConnectionError(f"Connection failed after {max_retries} attempts: {e}")
                    elif isinstance(e, FileNotFoundError): # Don't retry if file not found
                         raise StorageUploadError(f"Input file not found: {e}")
                    elif isinstance(e, ValueError): # Don't retry on bad input
                         raise e
                    else: # General upload error (includes S3Error other than AccessDenied, and other Exceptions)
                         raise StorageUploadError(f"Failed to upload file '{object_name}' after {max_retries} attempts: {e}")
                else:
                    # Wait before retrying
                    delay = base_delay * (2 ** attempt) # Exponential backoff
                    time.sleep(delay)

        # Fallback if loop finishes without success or raising (should not happen with current logic)
        raise StorageUploadError(f"Upload failed definitively for {object_name} after {max_retries} attempts.")

    def download_file_stream(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> HTTPResponse:
        """Download a file as a stream from MinIO storage.
        
        Args:
            object_name: Name/path of the object in storage
            bucket_name: Name of the bucket
        Returns:
            HTTPResponse: Response object containing the file stream
        """
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name if bucket_name is None else bucket_name,
                object_name=object_name
            )
            return response
        except S3Error as e:
            if 'NoSuchKey' in str(e):
                raise StorageFileNotFoundError(f"File not found: {object_name}")
            elif 'AccessDenied' in str(e):
                raise StorageAuthError(f"Access denied while downloading file: {e}")
            raise StorageDownloadError(f"Failed to download file: {e}")
        except ConnectionError as e:
            raise StorageConnectionError(f"Connection failed during download: {e}")
        except Exception as e:
            raise StorageDownloadError(f"Unexpected error during download: {e}")


    def download_file(
        self,
        object_name: str,
        file_path: Union[str, Path],
        bucket_name: Optional[str] = None
    ) -> Path:
        """Download a file from MinIO storage.
        
        Args:
            object_name: Name/path of the object in storage
            file_path: Local path to save the file
            
        Returns:
            Path: Path where file was saved
            
        Raises:
            StorageDownloadError: If download fails
            StorageFileNotFoundError: If file doesn't exist
            StorageConnectionError: If connection fails
        """
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.client.fget_object(
                bucket_name=self.bucket_name if bucket_name is None else bucket_name,
                object_name=object_name,
                file_path=str(file_path)
            )
            
            return file_path
            
        except S3Error as e:
            if 'NoSuchKey' in str(e):
                raise StorageFileNotFoundError(f"File not found: {object_name}")
            elif 'AccessDenied' in str(e):
                raise StorageAuthError(f"Access denied while downloading file: {e}")
            raise StorageDownloadError(f"Failed to download file: {e}")
        except ConnectionError as e:
            raise StorageConnectionError(f"Connection failed during download: {e}")
        except Exception as e:
            raise StorageDownloadError(f"Unexpected error during download: {e}")

    def delete_prefix(self, prefix: str, bucket_name: Optional[str] = None) -> int:
        """Bulk-delete every object under ``prefix``.

        MinIO has no real directories; a "folder" is just a shared key
        prefix. This is the entity-cascade cleanup path — single-file
        deletes should use ``delete_file``.

        Returns the number of objects removed. A missing prefix is not an
        error: returns 0.
        """
        from minio.deleteobjects import DeleteObject

        bucket = self.bucket_name if bucket_name is None else bucket_name
        try:
            objects = list(self.client.list_objects(
                bucket_name=bucket,
                prefix=prefix,
                recursive=True,
            ))
            if not objects:
                return 0
            delete_targets = [DeleteObject(obj.object_name) for obj in objects]
            errors = list(self.client.remove_objects(
                bucket_name=bucket,
                delete_object_list=iter(delete_targets),
            ))
            removed = len(delete_targets) - len(errors)
            return removed
        except S3Error as e:
            if 'AccessDenied' in str(e):
                raise StorageAuthError(f"Access denied while deleting prefix: {e}")
            raise StorageDeleteError(f"Failed to delete prefix {prefix}: {e}")
        except ConnectionError as e:
            raise StorageConnectionError(f"Connection failed during prefix deletion: {e}")

    def delete_file(self, object_name: str, bucket_name: str = None) -> bool:
        """Delete a file from MinIO storage.
        
        Args:
            object_name: Name/path of the object to delete
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            StorageDeleteError: If deletion fails
            StorageConnectionError: If connection fails
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name if bucket_name is None else bucket_name,
                object_name=object_name
            )
            return True
        except S3Error as e:
            if 'AccessDenied' in str(e):
                raise StorageAuthError(f"Access denied while deleting file: {e}")
            raise StorageDeleteError(f"Failed to delete file: {e}")
        except ConnectionError as e:
            raise StorageConnectionError(f"Connection failed during deletion: {e}")
        except Exception as e:
            raise StorageDeleteError(f"Unexpected error during deletion: {e}")

    def get_download_url(
        self,
        object_name: str,
        expires: Optional[datetime] = None,
        response_headers: Optional[Dict[str, str]] = None,
        bucket_name: Optional[str] = None
    ) -> str:
        """Get a pre-signed URL for downloading the file.
        
        Args:
            object_name: Name/path of the object
            expires: URL expiration time
            response_headers: Headers for the response
            
        Returns:
            str: Pre-signed URL
            
        Raises:
            StorageError: If URL generation fails
            StorageFileNotFoundError: If file doesn't exist
        """
        try:
            # Ensure file exists
            if not self.file_exists(object_name):
                raise StorageFileNotFoundError(f"File not found: {object_name}")
            
            # Default expiration of 7 days if not specified
            if expires is None:
                expires = timedelta(days=7)
            
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name if bucket_name is None else bucket_name,
                object_name=object_name,
                expires=expires,
                response_headers=response_headers
            )
        
            return url
            
        except S3Error as e:
            if 'AccessDenied' in str(e):
                raise StorageAuthError(f"Access denied while generating URL: {e}")
            raise StorageError(f"Failed to generate pre-signed URL: {e}")
        except ConnectionError as e:
            raise StorageConnectionError(f"Connection failed while generating URL: {e}")
        except Exception as e:
            raise StorageError(f"Unexpected error while generating URL: {e}")

    def list_files(
        self,
        prefix: Optional[str] = None,
        recursive: bool = True,
        bucket_name: Optional[str] = None
    ) -> list[str]:
        """List all files in MinIO storage with given prefix.

        Args:
            prefix: Filter files by prefix
            recursive: Search recursively in directories

        Returns:
            list[str]: List of file paths

        Raises:
            StorageError: If listing fails
            StorageConnectionError: If connection fails
        """
        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket_name if bucket_name is None else bucket_name,
                prefix=prefix,
                recursive=recursive
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            if 'AccessDenied' in str(e):
                raise StorageAuthError(f"Access denied while listing files: {e}")
            raise StorageError(f"Failed to list files: {e}")
        except ConnectionError as e:
            raise StorageConnectionError(f"Connection failed while listing files: {e}")
        except Exception as e:
            raise StorageError(f"Unexpected error while listing files: {e}")

    def list_files_paginated(
        self,
        prefix: Optional[str] = None,
        recursive: bool = True,
        bucket_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """List files with pagination, returning metadata from the list_objects iterator
        without making individual HEAD requests per file.

        Returns:
            dict with keys: files (list of dicts), total_count (int)
        """
        try:
            target_bucket = self.bucket_name if bucket_name is None else bucket_name
            objects = self.client.list_objects(
                bucket_name=target_bucket,
                prefix=prefix,
                recursive=recursive
            )

            all_files = []
            for obj in objects:
                if obj.is_dir:
                    continue
                all_files.append({
                    'bucket_name': target_bucket,
                    'object_name': obj.object_name,
                    'size': obj.size or 0,
                    'last_modified': obj.last_modified,
                    'etag': (obj.etag or '').strip('"'),
                    'content_type': obj.content_type,
                })

            total_count = len(all_files)
            page = all_files[offset:offset + limit]
            return {'files': page, 'total_count': total_count}
        except S3Error as e:
            if 'AccessDenied' in str(e):
                raise StorageAuthError(f"Access denied while listing files: {e}")
            raise StorageError(f"Failed to list files: {e}")
        except ConnectionError as e:
            raise StorageConnectionError(f"Connection failed while listing files: {e}")
        except Exception as e:
            raise StorageError(f"Unexpected error while listing files: {e}")

    def file_exists(self, object_name: str, bucket_name: str = None) -> bool:
        """Check if a file exists in MinIO storage.
        
        Args:
            object_name: Name/path of the object
            
        Returns:
            bool: True if file exists
            
        Raises:
            StorageConnectionError: If connection check fails
        """
        try:
            self.client.stat_object(
                bucket_name=self.bucket_name if bucket_name is None else bucket_name,
                object_name=object_name
            )
            return True
        except S3Error:
            return False
        except ConnectionError as e:
            raise StorageConnectionError(f"Connection failed while checking file: {e}")

    def get_file_metadata(self, object_name: str, bucket_name: str = None) -> Dict[str, Any]:
        """Get metadata for a file in MinIO storage.
        
        Args:
            object_name: Name/path of the object
            
        Returns:
            dict: File metadata including size, dates, content type and custom metadata
            
        Raises:
            StorageError: If metadata retrieval fails
            StorageFileNotFoundError: If file doesn't exist
            StorageConnectionError: If connection fails
        """
        try:
            stat = self.client.stat_object(
                bucket_name=self.bucket_name if bucket_name is None else bucket_name,
                object_name=object_name
            )
            
            return {
                'bucket_name': stat.bucket_name,
                'object_name': stat.object_name,
                'size': stat.size,
                'etag': stat.etag,
                'last_modified': stat.last_modified,
                'content_type': stat.content_type,
                'metadata': stat.metadata
            }
            
        except S3Error as e:
            if 'NoSuchKey' in str(e):
                raise StorageFileNotFoundError(f"File not found: {object_name}")
            elif 'AccessDenied' in str(e):
                raise StorageAuthError(f"Access denied while getting metadata: {e}")
            raise StorageError(f"Failed to get file metadata: {e}")
        except ConnectionError as e:
            raise StorageConnectionError(f"Connection failed while getting metadata: {e}")
        except Exception as e:
            raise StorageError(f"Unexpected error while getting metadata: {e}")

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists in MinIO storage.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            bool: True if bucket exists
            
        Raises:
            StorageConnectionError: If connection check fails
        """
        try:
            return self.client.bucket_exists(bucket_name)
        except S3Error:
            return False
        except ConnectionError as e:
            raise StorageConnectionError(f"Connection failed while checking bucket: {e}")


    def healthcheck(self) -> bool:
        """Check the connection to the MinIO server and bucket accessibility.

        Returns:
            bool: True if the connection is successful and the bucket is accessible.

        Raises:
            StorageConnectionError: If the connection fails or the bucket is not accessible.
        """
        try:
            # bucket_exists checks connection, authentication, and bucket presence
            self.client.bucket_exists(self.bucket_name)
            return True
        except S3Error as e:
            raise StorageConnectionError(f"MinIO healthcheck failed: {e}")
        except Exception as e:
            # Catch potential network errors or other unexpected issues
            raise StorageConnectionError(f"Unexpected error during MinIO healthcheck: {e}")
