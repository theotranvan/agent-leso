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
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""
    # Prix annuels (−17 %, 2 mois offerts). Optionnels : tant qu'ils ne sont pas
    # créés dans le dashboard Stripe, la facturation annuelle renvoie une erreur
    # claire au lieu de facturer au tarif mensuel.
    STRIPE_PRICE_STARTER_YEARLY: str = ""
    STRIPE_PRICE_PRO_YEARLY: str = ""
    STRIPE_PRICE_ENTERPRISE_YEARLY: str = ""

    # Email
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "agent@bet-agent.com"
    ADMIN_EMAIL: str = "admin@bet-agent.com"

    # Légifrance PISTE
    LEGIFRANCE_CLIENT_ID: str = ""
    LEGIFRANCE_CLIENT_SECRET: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Security
    # Optionnelle : requise par le Blueprint mais non utilisée pour chiffrer des
    # données partagées. La rendre optionnelle évite que le worker (où la clé est
    # en sync:false) crashe au boot si elle n'a pas été saisie manuellement.
    ENCRYPTION_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"

    # Monitoring
    SENTRY_DSN: str | None = None

    # Env
    ENVIRONMENT: Literal["development", "staging", "production"] = "production"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    # Origines CORS autorisées. "*" = tout (défaut, pour ne rien casser). Sinon
    # liste séparée par des virgules, ex: "https://app.exemple.ch,https://exemple.ch"
    ALLOWED_ORIGINS: str = "*"
    LOG_LEVEL: str = "INFO"

    # Bêta — interrupteur du paiement Stripe self-service.
    #   False (défaut) : paiement en ligne OUVERT, nouveaux comptes actifs,
    #     redirection Stripe à l'inscription.
    #   True : verrouille les boutons de paiement et crée les comptes inactifs
    #     (activation manuelle) — utile pour repasser en pilote fermé.
    # Surchargeable par la variable d'env BETA_MODE.
    BETA_MODE: bool = False
    BETA_BILLING_CONTACT_EMAIL: str = "contact@digitran.ch"

    # Domaines de prod toujours autorisés, même si ALLOWED_ORIGINS est mal réglé
    # (filet de sécurité : évite de verrouiller le SaaS sur une coquille de config).
    # Sûr car l'app s'authentifie par token Bearer, pas par cookie.
    _ALWAYS_ALLOWED_ORIGINS = ("https://leso.ch", "https://www.leso.ch")

    @property
    def cors_origins(self) -> list[str]:
        raw = (self.ALLOWED_ORIGINS or "*").strip()
        if raw == "*":
            return ["*"]
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        for o in self._ALWAYS_ALLOWED_ORIGINS:
            if o not in origins:
                origins.append(o)
        return origins

    # Forfaits — vocabulaire unique (solo / bureau / enterprise) partagé par le
    # marketing, Stripe et le quota tokens. Prix HT en CHF (TVA 8.1 % en sus).
    # `tokens` = garde-fou de coût interne ; `livrables` = volume affiché au
    # client (≈ 40 000 tokens par livrable). `seats` = 0 → illimité.
    PLAN_LIMITS: dict = Field(default_factory=lambda: {
        "solo": {
            "name": "Solo", "price_chf": 690, "price_eur": 690,
            "price_chf_yearly": 6900, "tokens": 8_000_000,
            "livrables": 200, "seats": 1, "tasks": 200,
        },
        "bureau": {
            "name": "Bureau", "price_chf": 2400, "price_eur": 2400,
            "price_chf_yearly": 24000, "tokens": 20_000_000,
            "livrables": 500, "seats": 0, "tasks": 500,
        },
        "enterprise": {
            "name": "Enterprise", "price_chf": 4900, "price_eur": 4900,
            "price_chf_yearly": 49000, "tokens": 60_000_000,
            "livrables": 1500, "seats": 0, "tasks": 100_000,
        },
    })

    RATE_LIMIT_PER_MINUTE: int = 100
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: set[str] = Field(default_factory=lambda: {
        "pdf", "docx", "ifc", "bcf", "xlsx", "xls", "png", "jpg", "jpeg", "tiff",
        "dxf", "dwg",  # plans CAO pour le relevé thermique 2D
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
