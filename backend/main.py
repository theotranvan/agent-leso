"""Point d'entrée FastAPI - BET Agent SaaS."""
import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware import SecurityHeadersMiddleware, limiter
from app.routes import (
    aeai, auth, bim as bim_routes, billing, dashboard, documents,
    idc, norms, projects, structure, tasks, thermique, veille,
)

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Sentry
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1 if settings.is_production else 1.0,
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    logger.info(f"🚀 BET Agent API démarré - env={settings.ENVIRONMENT}")
    # V2 - seed des normes CH au démarrage (idempotent)
    if settings.AUTO_SEED_NORMS:
        try:
            from app.ch.norms_catalog import all_seed_norms
            from app.database import get_supabase_admin
            admin = get_supabase_admin()
            count = admin.table("regulatory_norms").select("id", count="exact").limit(1).execute()
            if (count.count or 0) < 10:
                logger.info("📚 Seeding du catalogue de normes CH...")
                for norm in all_seed_norms():
                    try:
                        admin.table("regulatory_norms").upsert(
                            norm, on_conflict="reference"
                        ).execute()
                    except Exception as e:
                        logger.debug(f"Skip norme {norm['reference']}: {e}")
                logger.info("📚 Seed terminé")
        except Exception as e:
            logger.warning(f"Seed normes échoué au démarrage : {e}")
    yield
    logger.info("🛑 BET Agent API arrêté")


app = FastAPI(
    title="BET Agent API",
    description="SaaS agent IA pour bureaux d'études techniques - Swiss-first",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

# CORS restrictif
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Stripe-Signature"],
)

# Sécurité
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/", tags=["meta"])
async def root():
    return {"name": "BET Agent API", "version": "2.0.0", "status": "ok"}


@app.get("/health", tags=["meta"])
async def health():
    """Healthcheck pour UptimeRobot / Render."""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Fallback global - log + réponse générique (pas de détail interne en prod)."""
    logger.exception(f"Erreur non gérée: {exc}")
    if settings.is_production:
        return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# Routes versionnées /api/*
API_PREFIX = "/api"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(billing.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)

# V2 Swiss-first
app.include_router(thermique.router, prefix=API_PREFIX)
app.include_router(structure.router, prefix=API_PREFIX)
app.include_router(bim_routes.router, prefix=API_PREFIX)
app.include_router(idc.router, prefix=API_PREFIX)
app.include_router(aeai.router, prefix=API_PREFIX)
app.include_router(veille.router, prefix=API_PREFIX)
app.include_router(norms.router, prefix=API_PREFIX)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=not settings.is_production)
