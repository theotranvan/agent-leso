"""Routes catalogue de normes."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.database import get_supabase_admin
from app.middleware import AuthUser, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/norms", tags=["norms"])


@router.get("")
async def list_norms(
    user: Annotated[AuthUser, Depends(get_current_user)],
    domain: str | None = None,
    jurisdiction: str | None = None,
    quotable_only: bool = False,
    search: str | None = None,
    limit: int = 100,
):
    """Liste les normes, avec filtres."""
    admin = get_supabase_admin()
    q = admin.table("regulatory_norms").select("*")
    if domain:
        q = q.contains("domain", [domain])
    if jurisdiction:
        q = q.contains("jurisdiction", [jurisdiction])
    if quotable_only:
        q = q.eq("quotable", True)
    if search:
        q = q.or_(f"reference.ilike.%{search}%,title.ilike.%{search}%")
    r = q.order("authority").limit(limit).execute()
    return {"norms": r.data or [], "count": len(r.data or [])}


@router.get("/{norm_id}")
async def get_norm(
    norm_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    admin = get_supabase_admin()
    n = admin.table("regulatory_norms").select("*").eq("id", norm_id).maybe_single().execute()
    if not n.data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Norme introuvable")
    # Si non quotable, on assure que content_full est masqué
    if not n.data.get("quotable"):
        n.data["content_full"] = None
        n.data["content_notice"] = (
            "Cette norme est sous licence. Seul le résumé maison est disponible. "
            "Pour le texte intégral, consulter la source officielle."
        )
    return n.data
