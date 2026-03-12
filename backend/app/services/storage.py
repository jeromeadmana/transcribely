import os
import uuid
import shutil
from typing import Optional
from pathlib import Path

from app.core.config import settings


class LocalStorageService:
    """Local filesystem storage for development."""

    def __init__(self):
        self.base_path = Path(settings.local_storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def generate_upload_path(self, filename: str) -> tuple[str, str]:
        """Generate a unique storage path for uploading a file."""
        file_extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
        storage_key = f"videos/{uuid.uuid4()}.{file_extension}"
        full_path = self.base_path / storage_key

        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        return str(full_path), storage_key

    def get_file_path(self, storage_key: str) -> str:
        """Get full path for a storage key."""
        return str(self.base_path / storage_key)

    def save_uploaded_file(self, file_content: bytes, storage_key: str) -> None:
        """Save uploaded file content to storage."""
        dest_path = self.base_path / storage_key
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(file_content)

    def copy_file(self, source_path: str, storage_key: str) -> None:
        """Copy a file to storage."""
        dest_path = self.base_path / storage_key
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest_path)

    def delete_file(self, storage_key: str) -> None:
        """Delete a file from storage."""
        file_path = self.base_path / storage_key
        if file_path.exists():
            file_path.unlink()

    def file_exists(self, storage_key: str) -> bool:
        """Check if a file exists in storage."""
        return (self.base_path / storage_key).exists()

    def get_file_size(self, storage_key: str) -> Optional[int]:
        """Get file size in bytes."""
        file_path = self.base_path / storage_key
        if file_path.exists():
            return file_path.stat().st_size
        return None


class S3StorageService:
    """S3/MinIO storage for production."""

    def __init__(self):
        import boto3
        from botocore.config import Config

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        self.bucket = settings.s3_bucket

    def generate_upload_url(self, filename: str, content_type: Optional[str] = None) -> tuple[str, str]:
        """Generate a presigned URL for uploading a file."""
        file_extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
        storage_key = f"videos/{uuid.uuid4()}.{file_extension}"

        params = {
            "Bucket": self.bucket,
            "Key": storage_key,
        }
        if content_type:
            params["ContentType"] = content_type

        url = self.s3_client.generate_presigned_url(
            "put_object",
            Params=params,
            ExpiresIn=3600,
        )

        return url, storage_key

    def get_file_path(self, storage_key: str) -> str:
        """For S3, return the storage key (used for downloads)."""
        return storage_key

    def download_file(self, storage_key: str, local_path: str) -> None:
        """Download a file from storage to local path."""
        self.s3_client.download_file(self.bucket, storage_key, local_path)

    def upload_file(self, local_path: str, storage_key: str, content_type: Optional[str] = None) -> None:
        """Upload a file from local path to storage."""
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        self.s3_client.upload_file(local_path, self.bucket, storage_key, ExtraArgs=extra_args or None)

    def delete_file(self, storage_key: str) -> None:
        """Delete a file from storage."""
        from botocore.exceptions import ClientError
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=storage_key)
        except ClientError:
            pass

    def file_exists(self, storage_key: str) -> bool:
        """Check if a file exists in storage."""
        from botocore.exceptions import ClientError
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=storage_key)
            return True
        except ClientError:
            return False


# Create appropriate storage service based on config
if settings.storage_type == "local":
    storage_service = LocalStorageService()
else:
    storage_service = S3StorageService()
