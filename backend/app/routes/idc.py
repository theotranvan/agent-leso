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


# ============================================================
# V3 — Endpoints directs sur les connecteurs IDC
# ============================================================

@router.post("/v3/extract-facture")
async def v3_extract_facture(
    user: Annotated[AuthUser, Depends(get_current_user)],
    pdf: UploadFile = File(...),
    vector: str = Form("mazout"),
):
    """V3 : extrait valeur + unité + période depuis une facture PDF.

    Stratégie à 3 niveaux : PyMuPDF → Tesseract OCR → Claude Haiku Vision.
    """
    from app.connectors.idc.facture_extractor import FactureExtractor

    pdf_bytes = await pdf.read()
    if not pdf_bytes:
        raise HTTPException(400, "PDF vide")

    extractor = FactureExtractor(enable_claude_fallback=True)
    try:
        result = extractor.extract(pdf_bytes, vector=vector)
    except ValueError as e:
        raise HTTPException(400, str(e))

    audit_log(user, "v3_idc_extract_facture", {
        "vector": vector,
        "confidence": result.confidence,
        "method": result.extraction_method,
    })
    return result.to_dict()


@router.post("/v3/compute")
async def v3_compute_idc(
    user: Annotated[AuthUser, Depends(get_current_user)],
    body: dict,
):
    """V3 : calcule l'IDC annuel depuis une liste de consommations.

    Body attendu :
      {
        "sre_m2": 1250.0,
        "vector": "mazout",
        "affectation": "logement_collectif",
        "year": 2024,
        "dju_year": 3100.0,  (optionnel)
        "consumptions": [
          {"value": 5250, "unit": "litre", "period_start": "2024-01-01", "period_end": "2024-04-30"}
        ]
      }
    """
    from datetime import date
    from app.connectors.idc import IDCCalculator, IDCComputationInput
    from app.connectors.idc.idc_calculator import IDCConsumption

    try:
        sre = float(body["sre_m2"])
        vector = str(body["vector"])
        affectation = str(body.get("affectation", "logement_collectif"))
        year = int(body.get("year", date.today().year))
        dju_year = body.get("dju_year")
        consumptions_raw = body.get("consumptions") or []
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(400, f"Body invalide : {e}")

    if not consumptions_raw:
        raise HTTPException(400, "Au moins une consommation requise")

    consumptions = []
    for c in consumptions_raw:
        try:
            ps = c.get("period_start")
            pe = c.get("period_end")
            consumptions.append(IDCConsumption(
                raw_value=float(c["value"]),
                raw_unit=str(c.get("unit", "kwh")),
                period_start=date.fromisoformat(ps) if isinstance(ps, str) else None,
                period_end=date.fromisoformat(pe) if isinstance(pe, str) else None,
                source_document_id=c.get("source_doc_id"),
            ))
        except (KeyError, TypeError, ValueError) as e:
            raise HTTPException(400, f"Consommation invalide : {e}")

    calc = IDCCalculator()
    try:
        result = calc.compute(IDCComputationInput(
            sre_m2=sre, vector=vector, affectation=affectation,
            consumptions=consumptions, year=year,
            dju_year_measured=float(dju_year) if dju_year else None,
        ))
    except ValueError as e:
        raise HTTPException(400, str(e))

    audit_log(user, "v3_idc_compute", {
        "vector": vector, "year": year,
        "idc_normalized_kwh_m2_an": result.idc_normalized_kwh_m2_an,
        "classification": result.classification.status.value,
    })

    return {
        "idc_raw_kwh_m2_an": result.idc_raw_kwh_m2_an,
        "idc_normalized_kwh_m2_an": result.idc_normalized_kwh_m2_an,
        "idc_normalized_mj_m2_an": result.idc_normalized_mj_m2_an,
        "total_energy_kwh": result.total_energy_kwh,
        "climate_correction_factor": result.climate_correction_factor,
        "sre_m2": result.sre_m2,
        "year": result.year,
        "classification": {
            "status": result.classification.status.value,
            "label": result.classification.label,
            "action_required": result.classification.action_required,
            "color": result.classification.color,
        },
        "warnings": result.warnings,
        "details": result.details,
    }


@router.post("/v3/ocen-form")
async def v3_generate_ocen_form(
    user: Annotated[AuthUser, Depends(get_current_user)],
    body: dict,
):
    """V3 : génère un PDF préparatoire de déclaration OCEN."""
    from fastapi.responses import Response
    from datetime import date
    from app.connectors.idc import IDCCalculator, IDCComputationInput
    from app.connectors.idc.idc_calculator import IDCConsumption
    from app.connectors.idc.ocen_form_generator import OCENFormGenerator, OCENFormInput

    # Calcul IDC
    try:
        calc_in = body.get("calculation") or {}
        sre = float(calc_in["sre_m2"])
        vector = str(calc_in["vector"])
        year = int(calc_in.get("year", date.today().year))
        consumptions = [
            IDCConsumption(
                raw_value=float(c["value"]),
                raw_unit=str(c.get("unit", "kwh")),
                period_start=date.fromisoformat(c["period_start"]) if c.get("period_start") else None,
                period_end=date.fromisoformat(c["period_end"]) if c.get("period_end") else None,
            )
            for c in (calc_in.get("consumptions") or [])
        ]
        if not consumptions:
            raise HTTPException(400, "Consommations requises")

        idc_result = calc.compute(IDCComputationInput(
            sre_m2=sre, vector=vector,
            affectation=calc_in.get("affectation", "logement_collectif"),
            consumptions=consumptions, year=year,
            dju_year_measured=float(calc_in["dju_year"]) if calc_in.get("dju_year") else None,
        )) if False else IDCCalculator().compute(IDCComputationInput(
            sre_m2=sre, vector=vector,
            affectation=calc_in.get("affectation", "logement_collectif"),
            consumptions=consumptions, year=year,
            dju_year_measured=float(calc_in["dju_year"]) if calc_in.get("dju_year") else None,
        ))
    except (KeyError, ValueError) as e:
        raise HTTPException(400, f"Données calcul invalides : {e}")

    bldg = body.get("building") or {}
    form_input = OCENFormInput(
        egid=bldg.get("egid"),
        address=str(bldg.get("address", "")),
        postal_code=bldg.get("postal_code"),
        city=str(bldg.get("city", "Genève")),
        sre_m2=sre,
        heating_vector=vector,
        building_year=bldg.get("building_year"),
        nb_logements=bldg.get("nb_logements"),
        regie_name=bldg.get("regie_name"),
        regie_email=bldg.get("regie_email"),
        regie_phone=bldg.get("regie_phone"),
        declarant_name=bldg.get("declarant_name"),
    )

    gen = OCENFormGenerator()
    try:
        pdf_bytes = gen.generate(form_input, idc_result)
    except RuntimeError as e:
        raise HTTPException(500, f"Génération PDF échouée : {e}")

    audit_log(user, "v3_ocen_form_generate", {"size_bytes": len(pdf_bytes)})
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="OCEN_IDC_{year}_{bldg.get("egid") or "building"}.pdf"',
        },
    )
