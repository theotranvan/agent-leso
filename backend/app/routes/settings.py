"""Routes settings — configuration de l'organisation (charte client, préférences)."""
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_supabase_admin
from app.middleware import AuthUser, audit_log, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])


class BrandingConfigInput(BaseModel):
    full_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    logo_height_px: Optional[int] = 60
    primary_color: Optional[str] = "#1B2E4E"
    accent_color: Optional[str] = "#2E75B6"
    text_color: Optional[str] = "#222222"
    muted_color: Optional[str] = "#666666"
    font_family: Optional[str] = "Inter, Arial, sans-serif"
    base_font_size_pt: Optional[int] = 11
    signature_block: Optional[str] = None
    footer_text: Optional[str] = None
    confidentiality: Optional[str] = "Confidentiel"


@router.get("/branding")
async def get_branding(user: Annotated[AuthUser, Depends(get_current_user)]):
    """Retourne la config de charte de l'organisation."""
    admin = get_supabase_admin()
    org = admin.table("organizations").select(
        "name, branding_config"
    ).eq("id", user.organization_id).maybe_single().execute()
    if not org.data:
        raise HTTPException(404, "Organisation introuvable")
    return {
        "organization_name": org.data.get("name"),
        "branding_config": org.data.get("branding_config") or {},
    }


@router.put("/branding")
async def update_branding(
    body: BrandingConfigInput,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Met à jour la charte de l'organisation (admin uniquement)."""
    if user.role != "admin":
        raise HTTPException(403, "Droits admin requis pour modifier la charte")

    admin = get_supabase_admin()
    branding = {k: v for k, v in body.model_dump().items() if v is not None}

    admin.table("organizations").update({
        "branding_config": branding,
    }).eq("id", user.organization_id).execute()

    await audit_log(
        action="branding_updated",
        organization_id=user.organization_id,
        user_id=user.id,
        resource_type="organization",
        resource_id=user.organization_id,
        metadata={"fields": list(branding.keys())},
    )

    return {"status": "updated", "branding_config": branding}
