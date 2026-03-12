from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database - set via DATABASE_URL and SYNC_DATABASE_URL environment variables
    database_url: str  # Required - no default, must be set in .env
    sync_database_url: str  # Required - no default, must be set in .env

    # Storage - Local filesystem
    storage_type: str = "local"  # "local" or "s3"
    local_storage_path: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

    # S3/MinIO (optional, for production)
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "transcribely-videos"

    # JWT
    jwt_secret: str = "dev-secret-change-in-production-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Whisper
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # App
    environment: str = "development"  # "development" or "production"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    # Upload limits
    max_upload_size_mb: int = 500  # Max file size in MB

    # Plan limits (minutes per month)
    plan_limits: dict = {
        "free": 30,       # 30 minutes/month
        "starter": 300,   # 5 hours/month
        "pro": 1200,      # 20 hours/month
        "enterprise": -1,  # Unlimited (-1)
    }

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Ensure local storage directory exists
if settings.storage_type == "local":
    os.makedirs(settings.local_storage_path, exist_ok=True)
