# app/core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    All fields are required unless a default is provided.
    """

    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 300

    # ── Security ────────────────────────────────────────────────────────────
    SECRET_KEY: str
    ENVIRONMENT: str = "development"

    # ── External services ───────────────────────────────────────────────────
    HCAPTCHA_SECRET: str = ""
    RESEND_API_KEY: str = ""
    ADMIN_EMAIL: str = ""

    # ── App config ──────────────────────────────────────────────────────────
    WHATSAPP_GROUP_LINK: str = ""
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_MAX_AGE: int = 2_592_000          # 30 days in seconds
    SESSION_ABSOLUTE_TIMEOUT_DAYS: int = 7
    CSRF_TOKEN_MAX_AGE: int = 3_600           # 1 hour in seconds
    RATE_LIMIT_STORAGE_URI: str = "memory://"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "test"

    @property
    def async_database_url(self) -> str:
        """
        Convert standard postgres:// or postgresql:// URL to
        asyncpg-compatible postgresql+asyncpg:// scheme.
        Supabase provides standard URLs — this normalises them.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """
    Return cached Settings instance.
    Use this everywhere instead of instantiating Settings() directly.
    """
    return Settings()


# Module-level singleton for convenience imports:
# from app.core.config import settings
settings = get_settings()