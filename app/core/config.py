from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Bookstore API"

    DATABASE_URL: str = (
        "postgresql+psycopg://bookstore:bookstore@localhost:5432/bookstore"
    )
    # Leave empty to disable caching.
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 60

    # Celery uses a separate Redis database from the cache.
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # Mailpit in development (no auth / TLS).
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    MAIL_FROM: str = "Bookstore <orders@bookstore.dev>"

    SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Used by `python -m app.seed`
    ADMIN_EMAIL: str = "admin@bookstore.dev"
    ADMIN_PASSWORD: str = "admin12345"


settings = Settings()
