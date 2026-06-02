"""Module CCTP - Cahier des Clauses Techniques Particulières.

V6 — Consomme la knowledge_base CCTP : les prescriptions techniques réelles
(par CFC, par niveau de prestation) sont injectées dans le prompt. Le LLM ne
génère plus du texte ex nihilo : il assemble les clauses normalisées et les
contextualise au projet spécifique.

Pipeline :
  1. Charge la structure CCTP réelle du lot (build_cctp_structure_for_lot)
  2. Charge la charte client (branding)
  3. Le LLM contextualise les prescriptions au projet (puissances, contraintes site)
  4. Génère un PDF à la charte client via le système de templates
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from app.agent.rag import build_project_context, get_project_summary
from app.agent.router import call_llm, get_model_for_task
from app.database import get_storage, get_supabase_admin
from app.knowledge_base.cctp import build_cctp_structure_for_lot, get_lot_cctp
from app.knowledge_base.templates.charter import get_org_branding, render_document

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_CCTP = """Tu es un ingénieur CVSE senior d'un bureau d'études techniques de Suisse romande, \
spécialisé dans la rédaction de CCTP (Cahiers des Clauses Techniques Particulières) selon la norme SIA 451 \
et la structure CFC/eCCC-Bât.

On te fournit une structure de CCTP avec des PRESCRIPTIONS TECHNIQUES NORMALISÉES déjà rédigées \
(par article CFC, au niveau de prestation demandé). Ton travail n'est PAS de réinventer ces prescriptions, \
mais de :

1. Les CONTEXTUALISER au projet : adapter les puissances, surfaces, débits aux données réelles du projet.
2. Les COMPLÉTER : ajouter les prescriptions spécifiques liées aux contraintes du site (accès, contraintes \
   acoustiques, contraintes patrimoniales, etc.).
3. Les ORGANISER en un document cohérent et professionnel, prêt à être envoyé en appel d'offres.
4. RÉDIGER l'introduction du lot et les clauses générales contextualisées.

Règles impératives :
- Conserve TOUTES les prescriptions techniques fournies (puissances, COP, certifications, essais).
- Cite les normes exactement comme fournies, sans les reproduire textuellement.
- N'invente JAMAIS de valeurs techniques non fournies. Si une donnée manque, écris "[À COMPLÉTER : ...]".
- Ton factuel, prescriptif, professionnel. Pas de marketing.
- Structure en sections claires avec numéros d'articles CFC.
- Produis du HTML sémantique (h2 pour les sections CFC, h3 pour les articles, ul pour les prescriptions, \
  table pour les essais de réception)."""


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Exécute une tâche de rédaction CCTP avec la knowledge_base."""
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    lot = params.get("lot", "electricite")
    type_ouvrage = params.get("type_ouvrage", "")
    niveau = params.get("niveau_prestation", "standard")
    surface = params.get("surface", "")
    contraintes = params.get("contraintes", "")

    # 1. Charge la structure CCTP réelle depuis la knowledge_base
    lot_data = get_lot_cctp(lot)
    if not lot_data:
        # Lot non couvert par la KB : on signale clairement plutôt que d'improviser
        logger.warning("Lot %s non couvert par la knowledge_base CCTP", lot)
        cctp_structure = None
    else:
        cctp_structure = build_cctp_structure_for_lot(lot, niveau)

    project_info = await get_project_summary(org_id, project_id) if project_id else {}
    project_name = project_info.get("name") or params.get("project_name", "Projet")
    project_address = project_info.get("address") or ""
    canton = project_info.get("canton") or params.get("canton", "VD")

    context_query = f"CCTP lot {lot} {type_ouvrage} {contraintes}"
    rag_context = await build_project_context(context_query, org_id, project_id, top_k=6)

    # 2. Construit le prompt avec les prescriptions RÉELLES injectées
    if cctp_structure:
        kb_block = _format_kb_for_prompt(cctp_structure)
    else:
        kb_block = (
            f"Aucune bibliothèque de clauses n'est disponible pour le lot '{lot}'. "
            f"Indique clairement dans le document les sections qui nécessitent une rédaction manuelle "
            f"par l'ingénieur, et ne produis que la structure attendue."
        )

    user_content = f"""Rédiger le CCTP du lot pour le projet suivant.

## Données projet
- Projet : {project_name}
- Adresse : {project_address}
- Canton : {canton}
- Type d'ouvrage : {type_ouvrage or "non précisé"}
- Niveau de prestation demandé : {niveau}
- Surface concernée : {surface or "non précisée"} m²

## Contraintes particulières du projet
{contraintes or "Aucune contrainte particulière signalée."}

## PRESCRIPTIONS TECHNIQUES NORMALISÉES À INTÉGRER (issues de la bibliothèque métier)
{kb_block}

## Contexte documentaire du projet
{rag_context or "Aucun document de référence."}

## Ta tâche
Produis le CCTP complet en HTML sémantique. Contextualise chaque prescription au projet, \
complète avec les contraintes, rédige l'introduction et les clauses générales. \
Conserve toutes les valeurs techniques et normes fournies."""

    # Régénération
    from app.agent.prompts import (
        build_regeneration_instructions,
        get_model_override_for_regeneration,
    )
    regen_context = params.get("regeneration_context")
    regen_block = build_regeneration_instructions(regen_context)
    if regen_block:
        user_content += regen_block
    base_model = get_model_for_task("redaction_cctp")
    model_override = get_model_override_for_regeneration(regen_context, base_model)

    llm_result = await call_llm(
        task_type="redaction_cctp",
        system_prompt=SYSTEM_PROMPT_CCTP,
        user_content=user_content,
        max_tokens=8000,
        temperature=0.2,
        model_override=model_override,
        organization_id=org_id,
        task_id=task.get("id"),
    )

    body_html = llm_result["text"]
    # Nettoyage si le LLM a wrappé dans des balises markdown de code
    body_html = body_html.replace("```html", "").replace("```", "").strip()

    reference = f"CCTP-{lot.upper()[:4]}-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6]}"

    # 3. Génère le PDF à la charte client
    branding = await get_org_branding(org_id)
    lot_intitule = lot_data["lot_intitule"] if lot_data else lot.upper()

    full_html = render_document(
        doc_type="cctp",
        title=f"CCTP — Lot {lot_intitule}",
        subtitle=f"Niveau de prestation : {niveau} · Réf. {reference}",
        project_info={
            "Projet": project_name,
            "Adresse": project_address,
            "Canton": canton,
            "Lot": f"{lot_data['lot_code'] if lot_data else ''} — {lot_intitule}",
            "Niveau": niveau,
        },
        body_html=body_html,
        branding=branding,
        custom_signataire=params.get("author"),
    )

    pdf_bytes = _html_to_pdf(full_html)

    storage = get_storage()
    filename = f"CCTP_{lot}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = f"{org_id}/cctp/{task['id']}/{filename}"
    storage.upload(path, pdf_bytes, content_type="application/pdf")
    signed_url = storage.get_signed_url(path, expires_in=604800)

    admin = get_supabase_admin()
    admin.table("documents").insert({
        "organization_id": org_id,
        "project_id": project_id,
        "filename": filename,
        "file_type": "pdf",
        "storage_path": path,
        "processed": True,
    }).execute()

    # Preview lisible (extrait du texte sans HTML)
    import re
    preview_text = re.sub(r"<[^>]+>", " ", body_html)
    preview_text = re.sub(r"\s+", " ", preview_text).strip()

    return {
        "result_url": signed_url,
        "preview": preview_text[:600] + "..." if len(preview_text) > 600 else preview_text,
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
        "email_bytes": pdf_bytes,
        "email_filename": filename,
        "kb_used": bool(cctp_structure),
        "articles_count": sum(len(s["articles"]) for s in cctp_structure["sections"]) if cctp_structure else 0,
    }


def _format_kb_for_prompt(structure: dict) -> str:
    """Formate la structure CCTP de la knowledge_base pour le prompt LLM."""
    lines = [
        f"Lot {structure['lot_code']} — {structure['lot_intitule']} (niveau {structure['niveau_prestation']})",
        "",
        "INTRODUCTION TYPE DU LOT (à contextualiser) :",
        structure["introduction"],
        "",
        "CLAUSES GÉNÉRALES (à conserver et contextualiser) :",
    ]
    for clause in structure["clauses_generales"]:
        lines.append(f"- {clause}")
    lines.append("")

    for section in structure["sections"]:
        lines.append(f"### Section CFC {section['cfc']} — {section['intitule']}")
        for art in section["articles"]:
            lines.append(f"\n**Article {art['numero']} — {art['titre']}**")
            lines.append("Prescriptions techniques (niveau demandé) :")
            for key, val in art["prescriptions"].items():
                lines.append(f"  - {key.replace('_', ' ').capitalize()} : {val}")
            if art.get("essais_reception"):
                lines.append("Essais de réception à exiger :")
                for essai in art["essais_reception"]:
                    lines.append(f"  - {essai}")
            if art.get("normes_referencees"):
                lines.append(f"Normes : {', '.join(art['normes_referencees'])}")
            if art.get("autorisations"):
                lines.append(f"Autorisations cantonales : {json.dumps(art['autorisations'], ensure_ascii=False)}")
        lines.append("")

    return "\n".join(lines)


def _html_to_pdf(html: str) -> bytes:
    """Convertit le HTML complet en PDF via WeasyPrint."""
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except Exception as e:
        logger.error("WeasyPrint échec, fallback PDF minimal : %s", e)
        # Fallback : retourne le HTML en bytes (ne devrait pas arriver en prod)
        return html.encode("utf-8")
