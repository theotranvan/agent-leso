"""Agent IDC Genève — pipeline complet extraction factures → calcul OCEN → rapport + PDF."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from app.agent.router import call_llm
from app.agent.swiss.prompts_ch import get_prompt_ch
from app.connectors.idc import IDCCalculator, IDCComputationInput
from app.connectors.idc.facture_extractor import FactureExtractor
from app.connectors.idc.idc_calculator import IDCConsumption
from app.connectors.idc.ocen_form_generator import OCENFormGenerator, OCENFormInput
from app.database import get_storage, get_supabase_admin
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Pipeline IDC Genève : factures → calcul → rapport narratif + formulaire OCEN PDF.

    Input params attendus :
      - building: dict (egid, address, sre_m2, heating_vector, nb_logements, regie_name...)
      - year: int
      - dju_year: float (optionnel, DJU de l'année mesurée)
      - invoice_document_ids: list[str] (optionnel, factures déjà uploadées à extraire)
      - consumptions: list[dict] (optionnel, consommations déjà calculées)
    """
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    building = params.get("building") or {}
    if not building or not building.get("sre_m2") or not building.get("heating_vector"):
        raise ValueError("building avec sre_m2 et heating_vector requis")

    year = int(params.get("year", date.today().year))
    dju_year = params.get("dju_year")

    admin = get_supabase_admin()
    storage = get_storage()

    # 1. Collecte des consommations (soit extraction facture, soit déjà fournies)
    consumptions: list[IDCConsumption] = []
    extraction_notes: list[str] = []

    if params.get("consumptions"):
        for c in params["consumptions"]:
            ps = c.get("period_start")
            pe = c.get("period_end")
            consumptions.append(IDCConsumption(
                raw_value=float(c["value"]),
                raw_unit=str(c.get("unit", "kwh")),
                period_start=date.fromisoformat(ps) if isinstance(ps, str) else None,
                period_end=date.fromisoformat(pe) if isinstance(pe, str) else None,
                source_document_id=c.get("source_doc_id"),
            ))

    if params.get("invoice_document_ids"):
        extractor = FactureExtractor(enable_claude_fallback=True)
        for doc_id in params["invoice_document_ids"]:
            doc = admin.table("documents").select("*").eq("id", doc_id).maybe_single().execute()
            if not doc.data:
                extraction_notes.append(f"Document {doc_id} introuvable")
                continue
            try:
                pdf_bytes = storage.download(doc.data["storage_path"])
                result = extractor.extract(pdf_bytes, vector=building["heating_vector"])
                if result.value is None:
                    extraction_notes.append(
                        f"Extraction échouée pour {doc.data['filename']} "
                        f"(méthode={result.extraction_method}, conf={result.confidence:.2f})"
                    )
                    continue
                consumptions.append(IDCConsumption(
                    raw_value=result.value,
                    raw_unit=result.unit or "kwh",
                    period_start=result.period_start,
                    period_end=result.period_end,
                    source_document_id=doc_id,
                ))
                extraction_notes.append(
                    f"{doc.data['filename']}: {result.value} {result.unit} "
                    f"(confiance {result.confidence:.2f}, méthode {result.extraction_method})"
                )
            except Exception as exc:
                extraction_notes.append(f"Extraction {doc.data['filename']} échec : {exc}")

    if not consumptions:
        raise ValueError("Aucune consommation exploitable après extraction")

    # 2. Calcul IDC
    calc = IDCCalculator()
    idc_result = calc.compute(IDCComputationInput(
        sre_m2=float(building["sre_m2"]),
        vector=str(building["heating_vector"]),
        affectation=str(building.get("affectation", "logement_collectif")),
        consumptions=consumptions,
        year=year,
        dju_year_measured=float(dju_year) if dju_year else None,
    ))

    # 3. Génération formulaire OCEN PDF (déterministe)
    form_input = OCENFormInput(
        egid=building.get("egid"),
        address=str(building.get("address", "")),
        postal_code=building.get("postal_code"),
        city=str(building.get("city", "Genève")),
        sre_m2=float(building["sre_m2"]),
        heating_vector=str(building["heating_vector"]),
        building_year=building.get("building_year"),
        nb_logements=building.get("nb_logements"),
        regie_name=building.get("regie_name"),
        regie_email=building.get("regie_email"),
        regie_phone=building.get("regie_phone"),
        declarant_name=params.get("author") or building.get("declarant_name"),
    )
    ocen_pdf = OCENFormGenerator().generate(form_input, idc_result)

    # 4. Rapport narratif via LLM Sonnet
    system = get_prompt_ch("idc_rapport")
    user_content = f"""Produire un rapport IDC annuel pour le bâtiment ci-dessous.

BÂTIMENT
- Adresse : {building.get('address', '')}
- EGID : {building.get('egid') or 'non renseigné'}
- SRE : {building['sre_m2']} m²
- Affectation : {building.get('affectation', 'logement_collectif')}
- Vecteur chauffage : {building['heating_vector']}
- Année construction : {building.get('building_year') or 'n/a'}
- Nombre de logements : {building.get('nb_logements') or 'n/a'}

MESURES
- Année de mesure : {year}
- DJU année : {dju_year or 'normal utilisé'}
- Nombre de factures agrégées : {len(consumptions)}
- Énergie totale : {idc_result.total_energy_kwh} kWh

RÉSULTATS DU CALCUL OFFICIEL
- IDC brut : {idc_result.idc_raw_kwh_m2_an} kWh/m²·an
- IDC normalisé (climat) : {idc_result.idc_normalized_kwh_m2_an} kWh/m²·an
- Équivalent MJ : {idc_result.idc_normalized_mj_m2_an} MJ/m²·an
- Facteur de correction climatique : {idc_result.climate_correction_factor}

CLASSIFICATION INTERNE
- Statut : {idc_result.classification.status.value}
- Libellé : {idc_result.classification.label}
- Action recommandée : {idc_result.classification.action_required}

NOTES D'EXTRACTION
{chr(10).join("- " + n for n in extraction_notes) if extraction_notes else "Consommations fournies directement"}

WARNINGS CALCUL
{chr(10).join("- " + w for w in idc_result.warnings) if idc_result.warnings else "Aucun"}

Produire un rapport markdown structuré :
1. Identification du bâtiment
2. Synthèse (IDC + classification + action)
3. Détail des consommations et correction climatique
4. Recommandations (si IDC élevé : pistes d'assainissement SIA 380/1)
5. Mention : seuils indicatifs - à confirmer auprès de l'OCEN avant soumission
6. Responsabilité de l'ingénieur signataire"""

    llm_result = await call_llm(
        task_type="idc_geneve_rapport",
        system_prompt=system,
        user_content=user_content,
        max_tokens=3500,
        temperature=0.1,
    )

    md = llm_result["text"]
    body_html = markdown_to_html(md)
    rapport_pdf = render_pdf_from_html(
        body_html=body_html,
        title=f"Rapport IDC {year}",
        subtitle=f"{building.get('address', '')} — Genève",
        project_name=params.get("project_name", ""),
        author=params.get("author", ""),
        reference=f"IDC-{year}-{building.get('egid') or 'building'}",
    )

    # 5. Upload des 2 PDFs
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{org_id}/idc/{task['id']}"

    rapport_filename = f"rapport_IDC_{year}_{ts}.pdf"
    rapport_path = f"{base}/{rapport_filename}"
    storage.upload(rapport_path, rapport_pdf, content_type="application/pdf")
    rapport_url = storage.get_signed_url(rapport_path, expires_in=604800)

    ocen_filename = f"formulaire_OCEN_IDC_{year}_{ts}.pdf"
    ocen_path = f"{base}/{ocen_filename}"
    storage.upload(ocen_path, ocen_pdf, content_type="application/pdf")

    admin.table("documents").insert([
        {
            "organization_id": org_id,
            "project_id": project_id,
            "filename": rapport_filename,
            "file_type": "pdf",
            "storage_path": rapport_path,
            "processed": True,
        },
        {
            "organization_id": org_id,
            "project_id": project_id,
            "filename": ocen_filename,
            "file_type": "pdf",
            "storage_path": ocen_path,
            "processed": True,
        },
    ]).execute()

    return {
        "result_url": rapport_url,
        "preview": md[:500],
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
        "email_bytes": rapport_pdf,
        "email_filename": rapport_filename,
        "idc_kwh_m2_an": idc_result.idc_normalized_kwh_m2_an,
        "classification": idc_result.classification.status.value,
    }


async def execute_extraction(task: dict[str, Any]) -> dict[str, Any]:
    """Task dédiée extraction d'une facture en batch (Haiku + Vision fallback).

    Input params :
      - document_id: str
      - vector: str (gaz/mazout/pellet/chauffage_distance/pac_*/electrique)
    """
    params = task.get("input_params") or {}
    org_id = task["organization_id"]

    doc_id = params.get("document_id")
    vector = params.get("vector")
    if not doc_id or not vector:
        raise ValueError("document_id et vector requis")

    admin = get_supabase_admin()
    storage = get_storage()

    doc = admin.table("documents").select("*").eq("id", doc_id).eq(
        "organization_id", org_id,
    ).maybe_single().execute()
    if not doc.data:
        raise ValueError("Document introuvable")

    pdf_bytes = storage.download(doc.data["storage_path"])
    extractor = FactureExtractor(enable_claude_fallback=True)
    result = extractor.extract(pdf_bytes, vector=vector)

    preview = (
        f"{result.value} {result.unit} "
        f"(conf {result.confidence:.2f}, méthode {result.extraction_method})"
        if result.value else f"Échec (conf {result.confidence:.2f})"
    )

    return {
        "result_url": None,
        "preview": preview,
        "model": "claude-haiku-4-5" if result.extraction_method == "claude_haiku_vision" else None,
        "tokens_used": 0,
        "cost_eur": 0.001 if result.extraction_method == "claude_haiku_vision" else 0,
        "extraction": result.to_dict(),
    }
