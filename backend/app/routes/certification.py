"""Routes certification bureau — badge vérifiable et page publique."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.middleware import AuthUser, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/certification", tags=["certification"])


@router.get("/status")
async def certification_status(user: Annotated[AuthUser, Depends(get_current_user)]):
    """État de certification du bureau + progression."""
    from app.services.certification import (
        compute_certification,
        get_badge_embed_html,
        get_or_create_badge_token,
    )

    cert = compute_certification(user.organization_id)
    cert["badge_token"] = get_or_create_badge_token(user.organization_id)
    if cert["eligible"]:
        cert["embed_html"] = get_badge_embed_html(user.organization_id)
        cert["verify_url"] = f"https://bet-agent.ch/verify/{cert['badge_token']}"
    return cert


# Route publique de vérification (pas d'auth — c'est le but : pub + confiance)
public_router = APIRouter(prefix="/verify", tags=["public"])


@public_router.get("/{badge_token}", response_class=HTMLResponse)
async def verify_badge_public(badge_token: str):
    """Page publique de vérification d'un badge (accessible sans compte)."""
    from app.services.certification import verify_badge

    result = verify_badge(badge_token)
    if result.get("valid"):
        level_color = {"Or": "#C9A227", "Argent": "#8E9099", "Bronze": "#A97142"}.get(
            result["level"], "#1B3A5C"
        )
        html = f"""
        <html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Bureau certifié BET Agent</title></head>
        <body style="font-family:-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#f7f6f2;">
        <div style="text-align:center;padding:48px;background:#fff;border-radius:16px;box-shadow:0 2px 24px rgba(0,0,0,0.06);max-width:420px;">
        <div style="font-size:42px;color:{level_color};">✓</div>
        <h1 style="font-size:22px;color:#0a0a0a;margin:12px 0 4px;">{result['organization_name']}</h1>
        <div style="display:inline-block;padding:6px 16px;border-radius:99px;background:{level_color}1a;color:{level_color};font-weight:600;font-size:14px;margin:8px 0;">
          Bureau certifié BET Agent — {result['level']}
        </div>
        <p style="color:#525252;font-size:14px;margin:12px 0 0;">
          Ce bureau produit et valide ses dossiers techniques avec BET Agent.
          {result['approved_docs']} documents validés.
        </p>
        <p style="color:#a3a3a3;font-size:12px;margin:16px 0 0;">
          Vérification authentique · bet-agent.ch
        </p>
        </div></body></html>
        """
        return HTMLResponse(content=html)

    html = f"""
    <html><head><meta charset="utf-8"><title>Badge non vérifié</title></head>
    <body style="font-family:-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#f7f6f2;">
    <div style="text-align:center;padding:48px;background:#fff;border-radius:16px;max-width:420px;">
    <div style="font-size:42px;color:#9ca3af;">?</div>
    <h1 style="font-size:20px;color:#0a0a0a;margin:12px 0;">Badge non vérifiable</h1>
    <p style="color:#525252;font-size:14px;">{result.get('reason', 'Ce badge n''est pas valide.')}</p>
    </div></body></html>
    """
    return HTMLResponse(content=html, status_code=404)
