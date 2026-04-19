"""Routes veille réglementaire CH."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app.agent.swiss.veille_agent import run_veille_romande
from app.database import get_supabase_admin
from app.middleware import AuthUser, get_current_user, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/veille", tags=["veille"])


@router.get("/alerts")
async def alerts(
    user: Annotated[AuthUser, Depends(get_current_user)],
    limit: int = 50,
    level: str | None = None,
):
    """Liste les alertes réglementaires détectées."""
    admin = get_supabase_admin()
    q = admin.table("regulatory_changes").select("*")
    if level:
        q = q.eq("impact_level", level)
    r = q.order("detected_at", desc=True).limit(limit).execute()
    return {"alerts": r.data or []}


@router.post("/run-now")
async def run_now(user: Annotated[AuthUser, Depends(require_admin)]):
    """Déclenche manuellement un run de veille (admin uniquement).

    En temps normal, le cron ARQ s'en charge tous les jours à 06h.
    """
    result = await run_veille_romande()
    return result
