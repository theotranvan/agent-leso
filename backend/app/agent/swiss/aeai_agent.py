"""Agent AEAI — génération checklists incendie et rapports de conformité."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from app.agent.router import call_llm
from app.agent.swiss.prompts_ch import get_prompt_ch
from app.ch.aeai_templates import AEAI_TEMPLATES, get_template_for_building
from app.database import get_storage, get_supabase_admin
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)


async def execute_checklist(task: dict[str, Any]) -> dict[str, Any]:
    """Génère la checklist AEAI pour un projet donné (Haiku, déterministe + LLM pour adaptation).

    Input params :
      - building_type: habitation_faible|habitation_moyenne|habitation_elevee|
                       administration|erp_petit|erp_moyen|erp_grand|parking|industriel
      - height_m: float
      - nb_occupants_max: int
      - special_context: str (optionnel - ex: "parking souterrain 2 niveaux")
    """
    from app.models.aeai import AEAIChecklistItem

    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    building_type = params.get("building_type") or "habitation_faible"
    height_m = params.get("height_m")
    nb_occupants = params.get("nb_occupants_max")
    special_context = params.get("special_context", "")

    # Base déterministe
    template = get_template_for_building(building_type, height_m=height_m, nb_occupants=nb_occupants)

    base_items = template["items"]

    # Enrichissement LLM Haiku si contexte spécial
    if special_context:
        system = get_prompt_ch("aeai_checklist")
        user_content = f"""Enrichir la checklist AEAI pour ce contexte particulier :

TYPOLOGIE DE BASE : {building_type}
HAUTEUR : {height_m or 'non renseignée'} m
OCCUPANTS MAX : {nb_occupants or 'non renseigné'}

CONTEXTE PARTICULIER : {special_context}

CHECKLIST DE BASE (à enrichir, pas à remplacer) :
{json.dumps([i for i in base_items], ensure_ascii=False, indent=2)}

Retourner UNIQUEMENT un JSON strict (pas de markdown, pas de texte autour) :
{{
  "additional_items": [
    {{"code": "AEAI-X1", "category": "xxx", "question": "xxx", "status": "a_verifier"}}
  ]
}}

Maximum 8 items supplémentaires. Les codes doivent commencer par AEAI-X pour les distinguer."""

        try:
            llm = await call_llm(
                task_type="aeai_checklist_generation",
                system_prompt=system,
                user_content=user_content,
                max_tokens=1500,
                temperature=0.1,
            )
            raw = llm["text"].strip()
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                additional = json.loads(raw[start:end + 1]).get("additional_items", [])
                base_items.extend(additional[:8])
        except Exception as exc:
            logger.warning("Enrichissement LLM checklist AEAI échoué : %s", exc)

    # Création en DB
    admin = get_supabase_admin()
    created = admin.table("aeai_checklists").insert({
        "organization_id": org_id,
        "project_id": project_id,
        "building_type": building_type,
        "height_m": height_m,
        "nb_occupants_max": nb_occupants,
        "items": base_items,
        "status": "draft",
    }).execute()

    checklist_id = created.data[0]["id"] if created.data else None

    return {
        "result_url": None,
        "preview": (
            f"Checklist AEAI {building_type}: {len(base_items)} points "
            f"{'(enrichie LLM)' if special_context else ''}"
        ),
        "model": "claude-haiku-4-5" if special_context else None,
        "tokens_used": 0,
        "cost_eur": 0,
        "checklist_id": checklist_id,
        "nb_items": len(base_items),
    }


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Génère le rapport AEAI narratif PDF depuis une checklist existante.

    Input params :
      - checklist_id: str
      - author: str (ingénieur incendie)
      - project_name, project_address
    """
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    checklist_id = params.get("checklist_id")
    if not checklist_id:
        raise ValueError("checklist_id requis")

    admin = get_supabase_admin()
    result = admin.table("aeai_checklists").select("*").eq("id", checklist_id).eq(
        "organization_id", org_id,
    ).maybe_single().execute()
    if not result.data:
        raise ValueError("Checklist introuvable")

    checklist = result.data
    items = checklist.get("items") or []

    # Stats
    stats = {
        "total": len(items),
        "conforme": sum(1 for i in items if i.get("status") == "conforme"),
        "non_conforme": sum(1 for i in items if i.get("status") == "non_conforme"),
        "a_verifier": sum(1 for i in items if i.get("status") == "a_verifier"),
        "na": sum(1 for i in items if i.get("status") == "na"),
    }

    system = get_prompt_ch("aeai_rapport")
    user_content = f"""Produire un rapport AEAI professionnel depuis cette checklist.

BÂTIMENT
- Typologie : {checklist.get('building_type')}
- Hauteur : {checklist.get('height_m') or 'n/a'} m
- Occupants max : {checklist.get('nb_occupants_max') or 'n/a'}

STATISTIQUES
- Total points : {stats['total']}
- Conformes : {stats['conforme']}
- Non conformes : {stats['non_conforme']}
- À vérifier : {stats['a_verifier']}
- N/A : {stats['na']}

CHECKLIST
{json.dumps(items, ensure_ascii=False, indent=2)}

Produire un rapport markdown :
1. Identification du projet
2. Synthèse (+ indicateur conformité global : OK / À ACHEVER / NON CONFORME)
3. Tableau par catégorie avec statut et commentaire
4. Points critiques à traiter en priorité
5. Conclusion + mention : seul l'expert AEAI signataire engage sa responsabilité
6. Référence directives AEAI (sans reproduction du texte normatif)"""

    llm = await call_llm(
        task_type="aeai_rapport",
        system_prompt=system,
        user_content=user_content,
        max_tokens=3500,
        temperature=0.1,
    )

    md = llm["text"]
    pdf_bytes = render_pdf_from_html(
        body_html=markdown_to_html(md),
        title="Rapport AEAI — Conformité incendie",
        subtitle=f"Typologie : {checklist.get('building_type')}",
        project_name=params.get("project_name", ""),
        project_address=params.get("project_address", ""),
        author=params.get("author", ""),
        reference=f"AEAI-{datetime.now().strftime('%Y%m%d-%H%M')}",
    )

    storage = get_storage()
    filename = f"rapport_AEAI_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = f"{org_id}/aeai/{task['id']}/{filename}"
    storage.upload(path, pdf_bytes, content_type="application/pdf")
    signed_url = storage.get_signed_url(path, expires_in=604800)

    admin.table("documents").insert({
        "organization_id": org_id,
        "project_id": project_id,
        "filename": filename,
        "file_type": "pdf",
        "storage_path": path,
        "processed": True,
    }).execute()

    # Update status checklist si tout conforme
    if stats["non_conforme"] == 0 and stats["a_verifier"] == 0:
        admin.table("aeai_checklists").update({"status": "ready"}).eq("id", checklist_id).execute()

    return {
        "result_url": signed_url,
        "preview": md[:500],
        "model": llm["model"],
        "tokens_used": llm["tokens_used"],
        "cost_eur": llm["cost_eur"],
        "email_bytes": pdf_bytes,
        "email_filename": filename,
    }
