"""Agent rapport de chantier — génère un compte-rendu structuré à partir de
photos et de notes de terrain.

L'ingénieur prend des photos sur le chantier, ajoute quelques notes courtes,
et l'agent produit un rapport de visite structuré : observations, réserves,
non-conformités, et actions à suivre. Zéro saisie de rapport.

Utilise la vision du LLM pour décrire ce que montrent les photos, croisé avec
les notes de l'ingénieur. Le rapport reste à valider (responsabilité humaine).
"""
from __future__ import annotations

import base64
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from app.agent.router import call_llm
from app.database import get_storage, get_supabase_admin

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Tu es un ingénieur CVSE qui rédige un rapport de visite de chantier \
pour un bureau d'études technique de Suisse romande.

On te fournit des photos prises sur le chantier et des notes courtes de l'ingénieur. \
Ton rôle est de produire un rapport de visite structuré et professionnel.

Pour chaque photo / note, identifie :
- Ce qui est observé (état d'avancement, installation, défaut éventuel)
- S'il s'agit d'une simple observation, d'une réserve, ou d'une non-conformité
- L'action à suivre le cas échéant (qui doit faire quoi)

Règles :
- Reste factuel : décris ce que tu vois, ne spécule pas sur ce qui n'est pas visible.
- Si une photo montre un défaut potentiel (malfaçon, non-respect d'une norme), \
signale-le clairement comme "À VÉRIFIER" — c'est l'ingénieur qui tranche.
- N'invente jamais de mesures ou de valeurs précises non fournies.
- Classe les points par gravité : observation < réserve < non-conformité.
- Produis du HTML sémantique : un tableau des points avec colonnes \
(N°, Localisation, Observation, Type, Action, Responsable).

Réponds UNIQUEMENT avec un objet JSON de cette forme, sans texte autour :
{
  "synthese": "résumé en 2-3 phrases de l'état du chantier",
  "points": [
    {"localisation": "...", "observation": "...", "type": "observation|reserve|non_conformite",
     "action": "...", "responsable": "..."}
  ],
  "html": "<le rapport complet en HTML>"
}"""


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Génère le rapport de chantier.

    input_params attendus :
      - photo_document_ids: list[str]  (photos uploadées)
      - notes: str                     (notes de terrain de l'ingénieur)
      - project_name: str
      - visit_date: str (optionnel)
    """
    params = task.get("input_params") or {}
    storage = get_storage()
    admin = get_supabase_admin()

    photo_ids = params.get("photo_document_ids") or []
    notes = params.get("notes") or ""
    project_name = params.get("project_name") or ""
    visit_date = params.get("visit_date") or datetime.now().strftime("%d/%m/%Y")

    if not photo_ids and not notes:
        raise ValueError("Au moins une photo ou des notes sont requises")

    # Construit le contenu multimodal pour le LLM
    content: list[dict[str, Any]] = []

    # Ajoute les photos (limite à 8 pour rester raisonnable en tokens)
    photos_added = 0
    for pid in photo_ids[:8]:
        doc = (
            admin.table("documents").select("storage_path, mime_type, filename")
            .eq("id", pid).eq("organization_id", task["organization_id"])
            .maybe_single().execute()
        )
        if not doc.data:
            continue
        try:
            img_bytes = storage.download(doc.data["storage_path"])
            mime = doc.data.get("mime_type") or "image/jpeg"
            if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
                mime = "image/jpeg"
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime,
                    "data": base64.b64encode(img_bytes).decode(),
                },
            })
            content.append({
                "type": "text",
                "text": f"(Photo {photos_added + 1} : {doc.data.get('filename', '')})",
            })
            photos_added += 1
        except Exception as e:
            logger.warning("Photo %s non chargée : %s", pid, e)

    # Ajoute les notes
    content.append({
        "type": "text",
        "text": f"Notes de l'ingénieur lors de la visite du {visit_date} "
                f"(chantier {project_name}) :\n{notes or '(aucune note)'}\n\n"
                f"Produis le rapport de visite au format JSON demandé.",
    })

    llm_result = await call_llm(
        task_type="compte_rendu_reunion",  # Sonnet (vision + rédaction)
        system_prompt=SYSTEM_PROMPT,
        user_content=content,
        max_tokens=4000,
        temperature=0.2,
    )

    # Parse le JSON
    raw = llm_result["text"].strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1]) if raw.endswith("```") else "\n".join(raw.split("\n")[1:])
    start, end = raw.find("{"), raw.rfind("}")
    parsed = {"synthese": "", "points": [], "html": ""}
    if start != -1 and end != -1:
        try:
            parsed = json.loads(raw[start:end + 1])
        except json.JSONDecodeError as e:
            logger.error("Parse rapport chantier échec : %s", e)
            parsed["html"] = f"<h1>Rapport de visite</h1><p>{raw}</p>"

    # Génère le PDF à la charte
    document_html = parsed.get("html") or "<h1>Rapport de visite de chantier</h1>"
    pdf_bytes = await _render_pdf(document_html, project_name, visit_date, task["organization_id"])

    # Upload du résultat
    filename = f"Rapport_chantier_{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    storage_path = f"{task['organization_id']}/reports/{uuid.uuid4()}.pdf"
    signed_url = None
    try:
        storage.upload(storage_path, pdf_bytes, "application/pdf")
        signed_url = storage.create_signed_url(storage_path, 3600 * 24 * 7)
    except Exception as e:
        logger.warning("Upload rapport chantier échoué : %s", e)

    # Compte les non-conformités pour le preview
    points = parsed.get("points", [])
    nb_nc = sum(1 for p in points if p.get("type") == "non_conformite")
    nb_reserves = sum(1 for p in points if p.get("type") == "reserve")

    return {
        "result_url": signed_url,
        "document_html": document_html,
        "preview": parsed.get("synthese", "")[:500]
                   + f" — {len(points)} point(s), {nb_reserves} réserve(s), {nb_nc} non-conformité(s)",
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
        "email_bytes": pdf_bytes,
        "email_filename": filename,
        "photos_analyzed": photos_added,
        "points_count": len(points),
        # Vérification de cohérence pour le score de confiance
        "numeric_checks": {"a_des_points": len(points) > 0},
    }


async def _render_pdf(html: str, project_name: str, visit_date: str, org_id: str) -> bytes:
    """Rend le rapport en PDF à la charte du bureau."""
    try:
        from app.knowledge_base.templates.charter import get_org_branding
        from app.services.pdf_generator import render_pdf_from_html
        branding = get_org_branding(org_id)
        return render_pdf_from_html(
            body_html=html,
            title="Rapport de visite de chantier",
            subtitle=f"{project_name} — {visit_date}",
            project_name=project_name,
            author="",
            include_cover=True,
            branding=branding,
        )
    except Exception as e:
        logger.error("Render PDF rapport chantier échoué : %s", e)
        return html.encode("utf-8")
