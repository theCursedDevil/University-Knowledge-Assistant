"""MinIO S3 object storage service wrapper (C-DOCSVC storage adapter).

Manages bucket lifecycles, streaming uploads, file retrieval, and atomic deletions
for raw PDF knowledge documents.
"""

import io
from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error

from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.core.errors import ExternalServiceError

settings = get_settings()


class StorageService:
    """Client wrapper for MinIO / S3-compatible object storage operations."""

    def __init__(self):
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.secure = settings.MINIO_SECURE
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        """Lazy-loaded singleton MinIO client."""
        if self._client is None:
            self._client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
        return self._client

    def ensure_bucket_exists(self) -> None:
        """Verifies destination bucket exists in MinIO; creates it if absent."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                logger.info("MinIO bucket '%s' not found. Creating...", self.bucket_name)
                self.client.make_bucket(self.bucket_name)
                logger.info("MinIO bucket '%s' created successfully.", self.bucket_name)
        except Exception as exc:
            logger.error("Failed to verify/create MinIO bucket '%s': %s", self.bucket_name, exc)
            raise ExternalServiceError("MinIO", f"Bucket initialization failed: {exc}")

    def upload_file(
        self,
        object_name: str,
        data: bytes | BinaryIO,
        length: int,
        content_type: str = "application/pdf",
    ) -> str:
        """Uploads file content to MinIO bucket.

        Returns:
            The full storage path key (e.g. 'university-documents/documents/uuid/file.pdf').
        """
        self.ensure_bucket_exists()

        if isinstance(data, bytes):
            stream = io.BytesIO(data)
        else:
            stream = data

        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=stream,
                length=length,
                content_type=content_type,
            )
            storage_path = f"{self.bucket_name}/{object_name}"
            logger.info("Uploaded object to MinIO: %s (%d bytes)", storage_path, length)
            return storage_path
        except Exception as exc:
            logger.error("MinIO put_object failed for '%s': %s", object_name, exc)
            raise ExternalServiceError("MinIO", f"File upload failed: {exc}")

    def delete_file(self, object_name: str) -> None:
        """Removes an object from MinIO.

        Accepts either 'object_name' or 'bucket_name/object_name'.
        """
        clean_object_name = object_name
        if clean_object_name.startswith(f"{self.bucket_name}/"):
            clean_object_name = clean_object_name[len(self.bucket_name) + 1 :]

        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=clean_object_name,
            )
            logger.info("Deleted object from MinIO: %s/%s", self.bucket_name, clean_object_name)
        except Exception as exc:
            logger.error("MinIO delete failed for '%s': %s", clean_object_name, exc)
            raise ExternalServiceError("MinIO", f"File deletion failed: {exc}")

    def file_exists(self, object_name: str) -> bool:
        """Checks if an object exists in MinIO."""
        clean_object_name = object_name
        if clean_object_name.startswith(f"{self.bucket_name}/"):
            clean_object_name = clean_object_name[len(self.bucket_name) + 1 :]

        try:
            self.client.stat_object(self.bucket_name, clean_object_name)
            return True
        except S3Error as err:
            if err.code in ("NoSuchKey", "NoSuchBucket"):
                return False
            raise ExternalServiceError("MinIO", f"Stat check failed: {err}")
        except Exception:
            return False

    def get_file(self, object_name: str) -> bytes:
        """Downloads and returns file bytes from MinIO."""
        clean_object_name = object_name
        if clean_object_name.startswith(f"{self.bucket_name}/"):
            clean_object_name = clean_object_name[len(self.bucket_name) + 1 :]

        try:
            response = self.client.get_object(self.bucket_name, clean_object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except Exception as exc:
            logger.error("MinIO get_object failed for '%s': %s", clean_object_name, exc)
            raise ExternalServiceError("MinIO", f"File retrieval failed: {exc}")


storage_service = StorageService()
