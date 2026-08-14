from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Library Management System API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./library.db"
    max_borrowed_books: int = 3

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 120

    log_level: str = "INFO"
    log_file: str = "logs/library-api.log"

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
