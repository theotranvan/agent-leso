"""Routes AEAI : création de checklists incendie."""
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.ch.aeai_templates import build_checklist
from app.database import get_storage, get_supabase_admin
from app.middleware import AuthUser, audit_log, get_current_user
from app.models.aeai import AEAIChecklistCreate, AEAIChecklistUpdate
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/aeai", tags=["aeai"])


@router.post("/checklists", status_code=201)
async def create_checklist(
    body: AEAIChecklistCreate,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Crée une checklist AEAI pré-remplie pour une typologie de bâtiment."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    items = build_checklist(
        building_type=body.building_type,
        height_m=body.height_m,
        nb_occupants=body.nb_occupants_max,
    )

    admin = get_supabase_admin()
    r = admin.table("aeai_checklists").insert({
        "organization_id": user.organization_id,
        "project_id": body.project_id,
        "building_type": body.building_type,
        "height_class": body.height_class,
        "nb_occupants_max": body.nb_occupants_max,
        "items": items,
        "status": "draft",
    }).execute()

    await audit_log(
        action="aeai_checklist_created",
        organization_id=user.organization_id,
        user_id=user.id,
        resource_type="aeai_checklist",
        resource_id=(r.data[0]["id"] if r.data else None),
    )

    return r.data[0] if r.data else {}


@router.get("/checklists")
async def list_checklists(
    user: Annotated[AuthUser, Depends(get_current_user)],
    project_id: str | None = None,
):
    admin = get_supabase_admin()
    q = admin.table("aeai_checklists").select("*").eq("organization_id", user.organization_id)
    if project_id:
        q = q.eq("project_id", project_id)
    r = q.order("created_at", desc=True).execute()
    return {"checklists": r.data or []}


@router.get("/checklists/{checklist_id}")
async def get_checklist(
    checklist_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    admin = get_supabase_admin()
    r = admin.table("aeai_checklists").select("*").eq("id", checklist_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not r.data:
        raise HTTPException(status_code=404, detail="Checklist introuvable")
    return r.data


@router.patch("/checklists/{checklist_id}")
async def update_checklist(
    checklist_id: str,
    body: AEAIChecklistUpdate,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    payload = {}
    if body.items:
        payload["items"] = [i.model_dump() for i in body.items]
    if body.status:
        payload["status"] = body.status
        if body.status == "validated":
            payload["validated_by"] = user.id
            payload["validated_at"] = datetime.utcnow().isoformat()

    r = admin.table("aeai_checklists").update(payload).eq("id", checklist_id).eq("organization_id", user.organization_id).execute()
    if not r.data:
        raise HTTPException(status_code=404, detail="Checklist introuvable")
    return r.data[0]


@router.post("/checklists/{checklist_id}/export-pdf")
async def export_checklist_pdf(
    checklist_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Génère un PDF de rapport AEAI à partir de la checklist."""
    admin = get_supabase_admin()
    c = admin.table("aeai_checklists").select("*").eq("id", checklist_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not c.data:
        raise HTTPException(status_code=404, detail="Checklist introuvable")

    md = _checklist_to_md(c.data)
    pdf_bytes = render_pdf_from_html(
        body_html=markdown_to_html(md),
        title="Rapport AEAI - Checklist incendie",
        subtitle=c.data.get("building_type", ""),
        reference=f"AEAI-{datetime.now().strftime('%Y%m%d')}",
    )

    storage = get_storage()
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = f"{user.organization_id}/aeai/{checklist_id}/rapport_{ts}.pdf"
    storage.upload(path, pdf_bytes, content_type="application/pdf")

    admin.table("documents").insert({
        "organization_id": user.organization_id,
        "project_id": c.data.get("project_id"),
        "filename": f"AEAI_{c.data.get('building_type', '')}_{ts}.pdf",
        "file_type": "pdf",
        "storage_path": path,
        "processed": True,
    }).execute()

    return {"pdf_url": storage.get_signed_url(path, expires_in=604800)}


def _checklist_to_md(checklist: dict) -> str:
    items = checklist.get("items", [])
    by_severity = {"BLOQUANT": [], "IMPORTANT": [], "INFO": []}
    for i in items:
        by_severity.setdefault(i.get("severity", "INFO"), []).append(i)

    md = [f"# Rapport AEAI - {checklist.get('building_type', '')}"]
    md.append("")
    md.append(f"**Nombre de points** : {len(items)}")
    md.append(f"- Bloquants : {len(by_severity.get('BLOQUANT', []))}")
    md.append(f"- Importants : {len(by_severity.get('IMPORTANT', []))}")
    md.append(f"- Info : {len(by_severity.get('INFO', []))}")
    md.append("")

    for severity in ["BLOQUANT", "IMPORTANT", "INFO"]:
        subset = by_severity.get(severity, [])
        if not subset:
            continue
        md.append(f"## {severity}")
        md.append("")
        md.append("| Référence | Titre | Statut | Notes |")
        md.append("|---|---|---|---|")
        for i in subset:
            md.append(
                f"| {i.get('reference', '')} | {i.get('title', '')} | "
                f"{i.get('status', '')} | {i.get('notes', '')} |"
            )
        md.append("")

    md.append("\n---\n*Document à vérifier et compléter par un expert incendie qualifié. "
              "Les références AEAI citées renvoient aux directives en vigueur.*")
    return "\n".join(md)
