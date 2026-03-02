from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/webhooks"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/webhooks"
    )

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Delivery
    MAX_DELIVERY_ATTEMPTS: int = 5
    DELIVERY_TIMEOUT_SECONDS: float = 10.0
    RETRY_BASE_DELAY_SECONDS: float = 1.0
    RETRY_MAX_DELAY_SECONDS: float = 3600.0

    # Security
    ALLOW_PRIVATE_IPS: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    # Environment
    ENVIRONMENT: str = "production"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
