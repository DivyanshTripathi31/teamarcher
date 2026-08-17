from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://archer:archer_local_only@localhost:5432/archer"
    database_auto_create: bool = True
    jwt_secret: str
    jwt_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # A production EC2 host authenticates to S3 through its IAM role/default
    # AWS credential provider chain. Do not place access keys in production
    # configuration. Static credentials are retained only for local MinIO.
    s3_bucket: str = ""
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_endpoint_url: Optional[str] = None
    s3_public_endpoint_url: Optional[str] = None
    local_storage_dir: str = "/private/tmp/archer-object-storage"
    local_storage_public_base_url: str = "http://127.0.0.1:8000"
    seed_initial_users: bool = False
    initial_user_passwords_json: str = "{}"
    max_upload_mb: int = 50

@lru_cache
def get_settings() -> Settings:
    return Settings()
