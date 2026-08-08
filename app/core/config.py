from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Library Management System API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./library.db"
    max_borrowed_books: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()