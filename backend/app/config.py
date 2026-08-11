from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://archer:archer_local_only@localhost:5432/archer"
    jwt_secret: str
    jwt_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    s3_bucket: str
    aws_region: str = "us-east-1"
    aws_access_key_id: str
    aws_secret_access_key: str
    s3_endpoint_url: Optional[str] = None
    s3_public_endpoint_url: Optional[str] = None
    seed_initial_users: bool = False
    initial_user_passwords_json: str = "{}"
    max_upload_mb: int = 50

@lru_cache
def get_settings() -> Settings:
    return Settings()
