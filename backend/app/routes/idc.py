"""Routes IDC Genève : bâtiments, déclarations annuelles, extraction factures."""
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.ch.cantons.geneve import FORMULAIRES_GE, idc_status
from app.database import get_storage, get_supabase_admin
from app.middleware import AuthUser, audit_log, get_current_user
from app.models.idc import IDCBuildingCreate, IDCDeclarationCreate, IDCInvoiceItem
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html
from app.services.swiss.idc_geneva import (
    compute_annual_from_invoices,
    extract_consumption_from_invoice_pdf,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/idc", tags=["idc"])


@router.get("/forms")
async def forms_list():
    """Liste des formulaires IDC/GE disponibles."""
    return {"forms": FORMULAIRES_GE}


@router.post("/buildings", status_code=201)
async def create_building(
    body: IDCBuildingCreate,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    r = admin.table("idc_buildings").insert({
        "organization_id": user.organization_id,
        "project_id": body.project_id,
        "ega": body.ega,
        "address": body.address,
        "postal_code": body.postal_code,
        "sre_m2": body.sre_m2,
        "heating_energy_vector": body.heating_energy_vector,
        "building_year": body.building_year,
        "nb_logements": body.nb_logements,
        "regie_name": body.regie_name,
        "regie_email": body.regie_email,
    }).execute()
    return r.data[0] if r.data else {}


@router.get("/buildings")
async def list_buildings(user: Annotated[AuthUser, Depends(get_current_user)]):
    admin = get_supabase_admin()
    r = admin.table("idc_buildings").select("*").eq("organization_id", user.organization_id).order("created_at", desc=True).execute()
    return {"buildings": r.data or []}


@router.get("/buildings/{building_id}")
async def get_building(
    building_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    admin = get_supabase_admin()
    b = admin.table("idc_buildings").select("*").eq("id", building_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not b.data:
        raise HTTPException(status_code=404, detail="Bâtiment introuvable")

    # Load declarations
    decls = admin.table("idc_annual_declarations").select("*").eq("building_id", building_id).order("year", desc=True).execute()
    return {**b.data, "declarations": decls.data or []}


@router.post("/buildings/{building_id}/extract-invoice")
async def extract_invoice(
    building_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    pdf: UploadFile = File(..., description="Facture chaufferie PDF"),
):
    """Extrait une consommation depuis une facture PDF."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    b = admin.table("idc_buildings").select("heating_energy_vector").eq("id", building_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not b.data:
        raise HTTPException(status_code=404, detail="Bâtiment introuvable")

    pdf_bytes = await pdf.read()
    result = extract_consumption_from_invoice_pdf(pdf_bytes, b.data["heating_energy_vector"])

    # Store invoice
    storage = get_storage()
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = f"{user.organization_id}/idc/{building_id}/invoice_{ts}_{pdf.filename}"
    storage.upload(path, pdf_bytes, content_type="application/pdf")

    # Document record
    doc = admin.table("documents").insert({
        "organization_id": user.organization_id,
        "filename": pdf.filename or f"invoice_{ts}.pdf",
        "file_type": "pdf",
        "storage_path": path,
        "processed": True,
    }).execute()

    return {
        "extracted": result,
        "source_document_id": doc.data[0]["id"] if doc.data else None,
    }


@router.post("/declarations", status_code=201)
async def create_declaration(
    body: IDCDeclarationCreate,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Crée une déclaration IDC annuelle + génère le formulaire PDF."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    b = admin.table("idc_buildings").select("*").eq("id", body.building_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not b.data:
        raise HTTPException(status_code=404, detail="Bâtiment introuvable")

    building = b.data

    # Calcul
    invoices_data = [
        {
            "value": inv.value,
            "unit": inv.unit,
            "period_start": inv.period_start.isoformat() if inv.period_start else None,
            "period_end": inv.period_end.isoformat() if inv.period_end else None,
        }
        for inv in body.invoices
    ]
    affectation = "logement_collectif" if (building.get("nb_logements") or 0) > 1 else "logement_individuel"
    calc = compute_annual_from_invoices(
        invoices_data,
        sre_m2=float(building["sre_m2"]),
        vector=building["heating_energy_vector"],
        affectation=affectation,
    )

    # Create declaration
    decl = admin.table("idc_annual_declarations").insert({
        "building_id": body.building_id,
        "organization_id": user.organization_id,
        "year": body.year,
        "consumption_kwh": calc["consumption_kwh"],
        "idc_mj_m2": calc["idc_normalise_mj_m2"],
        "source_documents": [inv.source_document_id for inv in body.invoices if inv.source_document_id],
        "status": "draft",
        "notes": body.notes,
    }).execute()

    declaration = decl.data[0] if decl.data else {}

    # Génère PDF formulaire IDC
    md = _build_idc_form_md(building, declaration, calc)
    pdf_bytes = render_pdf_from_html(
        body_html=markdown_to_html(md),
        title=f"Déclaration IDC {body.year}",
        subtitle="Formulaire OCEN Genève (préparatoire)",
        project_name=building["address"],
        reference=f"IDC-{body.year}-{building.get('ega', declaration['id'][:8])}",
    )

    storage = get_storage()
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    pdf_path = f"{user.organization_id}/idc/{body.building_id}/declaration_{body.year}_{ts}.pdf"
    storage.upload(pdf_path, pdf_bytes, content_type="application/pdf")

    admin.table("idc_annual_declarations").update({
        "form_pdf_url": pdf_path,
    }).eq("id", declaration["id"]).execute()

    admin.table("documents").insert({
        "organization_id": user.organization_id,
        "filename": f"IDC_{body.year}_{building.get('address', '')[:20]}.pdf",
        "file_type": "pdf",
        "storage_path": pdf_path,
        "processed": True,
    }).execute()

    await audit_log(
        action="idc_declaration_created",
        organization_id=user.organization_id,
        user_id=user.id,
        resource_type="idc_declaration",
        resource_id=declaration["id"],
    )

    return {
        **declaration,
        "calc": calc,
        "pdf_url": storage.get_signed_url(pdf_path, expires_in=604800),
    }


def _build_idc_form_md(building: dict, declaration: dict, calc: dict) -> str:
    """Formulaire IDC genevois en markdown."""
    status = calc.get("status", {})
    md = f"""# Déclaration IDC annuelle - Canton de Genève

**Année de déclaration** : {declaration.get('year')}

## Identification du bâtiment

| Champ | Valeur |
|---|---|
| EGID | {building.get('ega', '—')} |
| Adresse | {building.get('address', '')} |
| Code postal | {building.get('postal_code', '')} |
| Année de construction | {building.get('building_year', '—')} |
| Nombre de logements | {building.get('nb_logements', '—')} |
| SRE (Surface de Référence Énergétique) | {building.get('sre_m2')} m² |
| Régie / gestionnaire | {building.get('regie_name', '—')} |

## Consommation énergétique

| Champ | Valeur |
|---|---|
| Vecteur énergétique | {building.get('heating_energy_vector', '')} |
| Consommation annuelle (kWh) | {calc.get('consumption_kwh'):,.0f} |
| Énergie totale (MJ) | {calc.get('energy_mj'):,.0f} |
| Nombre de factures | {calc.get('nb_invoices', 0)} |

## Calcul IDC

| Champ | Valeur |
|---|---|
| **IDC brut** | **{calc.get('idc_brut_mj_m2')} MJ/m²/an** |
| **IDC normalisé** | **{calc.get('idc_normalise_mj_m2')} MJ/m²/an** |
| Statut | **{status.get('label', '—')}** ({status.get('level', '—')}) |
| Action recommandée | {status.get('action', '—')} |

## Notes

Document préparatoire généré par BET Agent. À vérifier et signer par un responsable qualifié avant transmission à l'OCEN.

Références : LEn-GE (L 2 30), REn-GE (L 2 30.01). Se référer toujours aux documents officiels OCEN en vigueur.
"""
    return md


@router.get("/declarations")
async def list_declarations(
    user: Annotated[AuthUser, Depends(get_current_user)],
    building_id: str | None = None,
    year: int | None = None,
):
    admin = get_supabase_admin()
    q = admin.table("idc_annual_declarations").select("*").eq("organization_id", user.organization_id)
    if building_id:
        q = q.eq("building_id", building_id)
    if year:
        q = q.eq("year", year)
    r = q.order("year", desc=True).execute()
    return {"declarations": r.data or []}
