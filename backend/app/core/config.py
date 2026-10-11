from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Event Registration Service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/event_service"
    
    # MailHog
    MAILHOG_HOST: str = "mailhog"
    MAILHOG_SMTP_PORT: int = 1025
    MAILHOG_API_URL: str = "http://mailhog:8025"
    
    # Frontend / CORS
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
