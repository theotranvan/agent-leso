"""Auth JWT Supabase, rate limiting, headers sécurité, audit."""
import logging
from typing import Annotated, Optional

import httpx
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings
from app.database import get_supabase_admin

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])
security = HTTPBearer(auto_error=True)


class AuthUser(BaseModel):
    id: str
    email: str
    organization_id: str
    role: str
    access_token: str


_jwks_cache: dict | None = None


def _get_jwks(force_refresh: bool = False) -> dict:
    global _jwks_cache
    if _jwks_cache is None or force_refresh:
        url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_cache = httpx.get(url, timeout=10).json()
    return _jwks_cache


# Algorithmes acceptés explicitement. Empêche toute attaque de substitution
# d'algorithme (ex. "none", ou confusion RS256↔HS256) en refusant tout en-tête
# alg hors de cette liste AVANT décodage.
_ALLOWED_JWT_ALGS = frozenset({"HS256", "RS256", "ES256"})


def verify_supabase_jwt(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        # Whitelist stricte : un en-tête alg non prévu est rejeté d'emblée.
        if alg not in _ALLOWED_JWT_ALGS:
            raise HTTPException(
                status_code=401, detail="Algorithme de token non autorisé",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # HS256 = secret symétrique Supabase. Les algos asymétriques (RS/ES)
        # n'utilisent JAMAIS ce secret : on les vérifie uniquement via JWKS,
        # ce qui exclut la confusion clé publique → secret HMAC.
        if alg == "HS256":
            return jwt.decode(
                token, settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"], audience="authenticated",
            )

        try:
            return jwt.decode(
                token, _get_jwks(), algorithms=[alg], audience="authenticated",
            )
        except JWTError:
            return jwt.decode(
                token, _get_jwks(force_refresh=True), algorithms=[alg],
                audience="authenticated",
            )
    except JWTError as e:
        logger.warning(f"JWT invalide: {e}")
        raise HTTPException(status_code=401, detail="Token invalide ou expiré",
                            headers={"WWW-Authenticate": "Bearer"})


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> AuthUser:
    token = credentials.credentials
    payload = verify_supabase_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sans sub")

    admin = get_supabase_admin()
    result = admin.table("users").select("organization_id, role").eq("id", user_id).maybe_single().execute()
    if not result.data:
        raise HTTPException(status_code=403, detail="Utilisateur sans organisation")

    return AuthUser(
        id=user_id, email=payload.get("email", ""),
        organization_id=result.data["organization_id"],
        role=result.data.get("role", "member"), access_token=token,
    )


async def require_admin(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Droits administrateur requis")
    return user


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
            "connect-src 'self' https://*.supabase.co https://api.anthropic.com; "
            "frame-ancestors 'none';"
        )
        return response


async def check_quota(user: AuthUser) -> None:
    admin = get_supabase_admin()
    org = admin.table("organizations").select(
        "tasks_used_this_month, tasks_limit, active"
    ).eq("id", user.organization_id).maybe_single().execute()
    if not org.data:
        raise HTTPException(status_code=403, detail="Organisation introuvable")
    if not org.data.get("active", True):
        raise HTTPException(
            status_code=403,
            detail=(
                "Compte en attente d'activation. Pendant la bêta, l'activation "
                f"d'un forfait se fait sur demande : {settings.BETA_BILLING_CONTACT_EMAIL}"
            ),
        )
    used = org.data.get("tasks_used_this_month", 0)
    limit = org.data.get("tasks_limit", 0)
    if used >= limit:
        raise HTTPException(status_code=429,
            detail=f"Quota mensuel atteint ({used}/{limit}). Passez au plan supérieur.")


async def audit_log(
    action: str, organization_id: Optional[str] = None, user_id: Optional[str] = None,
    resource_type: Optional[str] = None, resource_id: Optional[str] = None,
    ip_address: Optional[str] = None, metadata: Optional[dict] = None,
) -> None:
    try:
        get_supabase_admin().table("audit_logs").insert({
            "organization_id": organization_id, "user_id": user_id,
            "action": action, "resource_type": resource_type,
            "resource_id": resource_id, "ip_address": ip_address,
            "metadata": metadata or {},
        }).execute()
    except Exception as e:
        logger.error(f"Audit log failed: {e}")
