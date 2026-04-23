"""Agent réponse aux observations d'autorité (DALE Genève, DGT Vaud, autres).

Quand l'autorité cantonale renvoie un courrier d'observations sur un dossier d'enquête
(APA/APC), l'ingénieur doit rédiger une réponse point par point. Ce processus
prend typiquement 1-3 jours par affaire.

Pipeline :
1. Parse le PDF du courrier d'autorité (PyMuPDF)
2. Détecte les observations numérotées + le thème de chacune
3. Pour chaque observation : génère une réponse argumentée + référence norme
4. Assemble la lettre de réponse professionnelle en PDF

L'ingénieur signataire relit, complète si besoin, signe.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

from app.agent.router import call_llm
from app.agent.swiss.prompts_ch import get_prompt_ch
from app.database import get_storage, get_supabase_admin
from app.services.pdf_extractor import extract_text_from_pdf
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)


# Patterns typiques d'observations numérotées
OBSERVATION_PATTERNS = [
    # "Observation n°1", "Observation 1", "Remarque 1"
    re.compile(r"^\s*(?:observation|remarque|point|objection)\s*(?:n[°o]?)?\s*(\d+)\s*[:.\-)]",
               re.IGNORECASE | re.MULTILINE),
    # "1.", "1)", "1 -"
    re.compile(r"^\s*(\d+)\s*[.)\-]\s+\S", re.MULTILINE),
    # "§1", "§ 1"
    re.compile(r"^\s*§\s*(\d+)", re.MULTILINE),
]


THEMATIC_KEYWORDS: dict[str, list[str]] = {
    "energie_sia_380_1": ["énergie", "energie", "sia 380", "qh", "chauffage", "ep ", "enveloppe thermique", "u-value"],
    "incendie_aeai": ["incendie", "aeai", "compartimentage", "évacuation", "echappement", "feu"],
    "structure_sia_260": ["sia 260", "sia 262", "charge", "poutre", "poteau", "structure", "séisme", "sisme"],
    "idc_ocen": ["idc", "indice", "depense chaleur", "ocen", "assainissement"],
    "acoustique_sia_181": ["acoustique", "bruit", "sia 181", "nuisance sonore"],
    "gabarit_zone": ["gabarit", "hauteur", "distance", "limite", "zone", "alignement", "ius", "ibus"],
    "accessibilite_sia_500": ["accessib", "sia 500", "mobilité réduite", "pmr", "handicap"],
    "ldtr": ["ldtr", "loyer", "transformation", "demolition"],
    "paysage_arbres": ["arbre", "abattage", "paysage", "patrimoine", "inventaire"],
    "stationnement": ["stationnement", "parking", "place de parc", "mobilité"],
    "voisinage_droit": ["opposition", "voisin", "droit de recours", "procédure"],
}


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Produit la lettre de réponse aux observations.

    Input params :
      - observations_document_id: str (PDF du courrier autorité uploadé)
        OU
      - observations_text: str (texte brut du courrier)
      - authority: str ('DALE' | 'DGT' | 'SAT' | autre)
      - project_name, project_address
      - author: str (signataire — architecte ou ingénieur)
      - our_reference: str (notre référence)
      - their_reference: str (référence de l'autorité)
      - project_context: dict (données du projet pour argumenter)
    """
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    admin = get_supabase_admin()
    storage = get_storage()

    # 1. Récupération du texte des observations
    observations_text = params.get("observations_text") or ""
    doc_id = params.get("observations_document_id")
    source_name = "Courrier saisi manuellement"

    if doc_id:
        doc = admin.table("documents").select("*").eq("id", doc_id).eq(
            "organization_id", org_id,
        ).maybe_single().execute()
        if not doc.data:
            raise ValueError(f"Document {doc_id} introuvable")
        pdf_bytes = storage.download(doc.data["storage_path"])
        extracted, _ = extract_text_from_pdf(pdf_bytes)
        observations_text = extracted
        source_name = doc.data["filename"]

    if not observations_text or len(observations_text.strip()) < 50:
        raise ValueError("Texte des observations vide ou trop court (<50 char)")

    # 2. Détection structurée des observations
    observations = _parse_observations(observations_text)
    logger.info("Détecté %d observations dans le courrier %s", len(observations), source_name)

    if not observations:
        # Fallback : tout le texte est une observation unique
        observations = [{
            "num": 1,
            "title": "Observation globale",
            "text": observations_text[:3000],
            "theme": "general",
        }]

    # 3. Génération des réponses via LLM Sonnet (1 appel pour tout le courrier)
    authority = params.get("authority", "autorité cantonale")
    project_name = params.get("project_name", "")
    project_ctx = params.get("project_context") or {}

    system = get_prompt_ch("observations_autorite")
    user_content = f"""Produire une LETTRE DE RÉPONSE à un courrier d'observations transmis par {authority}.

CONTEXTE PROJET
- Nom : {project_name}
- Adresse : {params.get('project_address', '')}
- Canton : {project_ctx.get('canton', '?')}
- Affectation : {project_ctx.get('affectation', '?')}
- Opération : {project_ctx.get('operation_type', '?')}
- SRE : {project_ctx.get('sre_m2', '?')} m²
- Phase : {project_ctx.get('phase', '?')}

RÉFÉRENCES
- Notre réf : {params.get('our_reference', '')}
- Leur réf : {params.get('their_reference', '')}

OBSERVATIONS DE L'AUTORITÉ (détectées automatiquement)
{json.dumps(observations, ensure_ascii=False, indent=2)}

INSTRUCTIONS
Pour chaque observation, produire une RÉPONSE structurée :
1. Reformuler brièvement l'observation (1-2 phrases)
2. Réponse technique argumentée (mesure prise, justification, référence normative sans reproduction)
3. Pièce(s) modifiée(s) ou ajoutée(s) si applicable

La lettre doit avoir :
- En-tête : destinataire, références, objet, date
- Introduction courtoise (1 paragraphe)
- Réponses numérotées dans l'ordre des observations
- Conclusion + disposition à compléter
- Signature du professionnel responsable

Ton : respectueux, factuel, technique, PAS défensif. Les autorités apprécient les réponses
directes et sourcées. Ne jamais contredire frontalement - toujours reformuler et argumenter.

Ne JAMAIS affirmer de conformité définitive : seul le signataire engage sa responsabilité.

Produire la lettre complète en markdown."""

    llm = await call_llm(
        task_type="coordination_inter_lots",  # Sonnet pour raisonnement structuré
        system_prompt=system,
        user_content=user_content,
        max_tokens=6000,
        temperature=0.1,
    )

    md = llm["text"]

    # 4. Assemblage PDF
    author = params.get("author", "")
    pdf_bytes = render_pdf_from_html(
        body_html=markdown_to_html(md),
        title=f"Réponse aux observations — {authority}",
        subtitle=f"Ref. {params.get('their_reference', '')}",
        project_name=project_name,
        project_address=params.get("project_address", ""),
        author=author,
        reference=params.get("our_reference") or f"REP-{datetime.now().strftime('%Y%m%d-%H%M')}",
    )

    storage = get_storage()
    filename = f"reponse_observations_{authority}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = f"{org_id}/observations/{task['id']}/{filename}"
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

    return {
        "result_url": signed_url,
        "preview": md[:500],
        "model": llm["model"],
        "tokens_used": llm["tokens_used"],
        "cost_eur": llm["cost_eur"],
        "email_bytes": pdf_bytes,
        "email_filename": filename,
        "nb_observations": len(observations),
        "themes_detected": list({o["theme"] for o in observations}),
    }


def _parse_observations(text: str) -> list[dict[str, Any]]:
    """Détecte les observations numérotées dans le texte et classe par thème."""
    observations: list[dict[str, Any]] = []

    # Tentative avec chacun des patterns, on prend celui qui trouve le plus
    best_matches: list[tuple[int, int]] = []  # (num, position)
    best_pattern_name = None

    for pattern in OBSERVATION_PATTERNS:
        matches = [(int(m.group(1)), m.start()) for m in pattern.finditer(text)]
        if len(matches) > len(best_matches):
            best_matches = matches
            best_pattern_name = pattern.pattern

    if not best_matches:
        return []

    # Trier par position et découper le texte entre matches successifs
    best_matches.sort(key=lambda x: x[1])

    for i, (num, start_pos) in enumerate(best_matches):
        end_pos = best_matches[i + 1][1] if i + 1 < len(best_matches) else len(text)
        chunk = text[start_pos:end_pos].strip()
        if len(chunk) < 15:
            continue

        # Extrait la 1ère ligne comme titre
        first_line = chunk.split("\n")[0][:200]
        # Nettoie en retirant le préfixe numéroté
        title = re.sub(r"^\s*(?:observation|remarque|point|§)?\s*(?:n[°o]?)?\s*\d+\s*[:.\-)]\s*",
                       "", first_line, flags=re.IGNORECASE).strip() or f"Observation {num}"

        theme = _classify_theme(chunk.lower())

        observations.append({
            "num": num,
            "title": title[:150],
            "text": chunk[:2500],  # cap pour prompt
            "theme": theme,
        })

    return observations


def _classify_theme(text_lower: str) -> str:
    """Retourne le thème dominant selon les mots-clés détectés."""
    scores: dict[str, int] = {}
    for theme, keywords in THEMATIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[theme] = score
    if not scores:
        return "general"
    return max(scores.items(), key=lambda x: x[1])[0]
