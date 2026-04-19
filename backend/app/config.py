"""Configuration centralisée via pydantic-settings."""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",
                                       case_sensitive=True, extra="ignore")

    # LLM
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_STORAGE_BUCKET: str = "bet-documents"

    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PRICE_STARTER: str
    STRIPE_PRICE_PRO: str
    STRIPE_PRICE_ENTERPRISE: str

    # Email
    RESEND_API_KEY: str
    FROM_EMAIL: str = "agent@bet-agent.com"
    ADMIN_EMAIL: str = "admin@bet-agent.com"

    # Légifrance PISTE
    LEGIFRANCE_CLIENT_ID: str
    LEGIFRANCE_CLIENT_SECRET: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Security
    ENCRYPTION_KEY: str
    JWT_ALGORITHM: str = "HS256"

    # Monitoring
    SENTRY_DSN: str | None = None

    # Env
    ENVIRONMENT: Literal["development", "staging", "production"] = "production"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    LOG_LEVEL: str = "INFO"

    PLAN_LIMITS: dict = Field(default_factory=lambda: {
        "starter": {"tasks": 500, "price_eur": 690, "price_chf": 690},
        "pro": {"tasks": 2000, "price_eur": 1900, "price_chf": 1900},
        "enterprise": {"tasks": 999_999, "price_eur": 5000, "price_chf": 5000},
    })

    RATE_LIMIT_PER_MINUTE: int = 100
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: set[str] = Field(default_factory=lambda: {
        "pdf", "docx", "ifc", "bcf", "xlsx", "xls", "png", "jpg", "jpeg", "tiff"
    })

    # V2 - Suisse
    AUTO_SEED_NORMS: bool = True
    DEFAULT_COUNTRY: Literal["CH", "FR"] = "CH"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
