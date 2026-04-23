"""Pipeline d'ingestion documents pour les agents CH.

Ce module fait le pont entre les documents uploadés dans un projet et les agents.
Au lancement d'une tâche, il enrichit automatiquement `input_params` avec :
  - Les documents pertinents pour la tâche (matching par mots-clés + classification IA)
  - Leur contenu extrait (texte PDF, structure IFC, données XLSX)
  - Un résumé contextualisé injecté dans le prompt

Le design reste déterministe : chaque tâche déclare ce qu'elle attend, et l'ingesteur
délivre uniquement ces données — pas de "IA qui devine tout".
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# Déclaration des besoins documentaires par type de tâche
TASK_DOCUMENT_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "justificatif_sia_380_1": {
        "required_types": ["ifc", "pdf"],
        "keywords": ["thermique", "energie", "enveloppe", "sia_380", "minergie", "cecb"],
        "max_documents": 10,
    },
    "note_calcul_sia_260_267": {
        "required_types": ["ifc", "pdf", "xlsx"],
        "keywords": ["structure", "porteur", "sia_260", "sia_262", "acier", "beton"],
        "max_documents": 15,
    },
    "descriptif_can_sia_451": {
        "required_types": ["pdf", "docx"],
        "keywords": ["cctp", "descriptif", "can", "sia_451", "lot"],
        "max_documents": 20,
    },
    "controle_reglementaire_geneve": {
        "required_types": ["pdf"],
        "keywords": ["plan", "lci", "leng", "ldtr", "geneve"],
        "max_documents": 15,
    },
    "idc_geneve_rapport": {
        "required_types": ["pdf"],
        "keywords": ["facture", "mazout", "gaz", "consommation", "chaufferie", "idc"],
        "max_documents": 30,  # historique factures multi-années
    },
    "dossier_mise_enquete": {
        "required_types": ["pdf", "xlsx"],
        "keywords": [
            "plan", "situation", "surface", "sia_416", "cadastre",
            "energie", "aeai", "mobilite", "ldtr", "permis",
        ],
        "max_documents": 30,
    },
    "reponse_observations_autorite": {
        "required_types": ["pdf"],
        "keywords": ["dale", "dgt", "camac", "observation", "autorite", "courrier"],
        "max_documents": 5,
    },
    "metres_automatiques_ifc": {
        "required_types": ["ifc"],
        "keywords": [],
        "max_documents": 1,
    },
    "aeai_rapport": {
        "required_types": ["pdf"],
        "keywords": ["aeai", "incendie", "evacuation", "compartiment"],
        "max_documents": 10,
    },
    "prebim_generation": {
        "required_types": ["pdf", "docx"],
        "keywords": ["programme", "surface", "etage", "locaux"],
        "max_documents": 5,
    },
    "simulation_energetique_rapide": {
        "required_types": [],
        "keywords": [],
        "max_documents": 0,  # Pas de document requis - programme texte pur
    },
    "redaction_cctp": {
        "required_types": ["pdf", "docx"],
        "keywords": ["cctp", "descriptif", "lot", "prestation"],
        "max_documents": 15,
    },
    "chiffrage_dpgf": {
        "required_types": ["pdf", "xlsx"],
        "keywords": ["dpgf", "dqe", "prix", "quantitatif"],
        "max_documents": 15,
    },
    "coordination_inter_lots": {
        "required_types": ["pdf", "bcf"],
        "keywords": ["coordination", "clash", "bcf", "inter-lot"],
        "max_documents": 10,
    },
}


@dataclass
class IngestionResult:
    """Résultat d'une ingestion pour une tâche donnée."""

    documents_attached: list[dict[str, Any]] = field(default_factory=list)
    auto_params: dict[str, Any] = field(default_factory=dict)
    rag_context: str = ""
    warnings: list[str] = field(default_factory=list)

    def merge_into(self, input_params: dict[str, Any]) -> dict[str, Any]:
        """Injecte les résultats dans input_params sans écraser les valeurs existantes."""
        merged = dict(input_params)

        if "existing_documents" not in merged and self.documents_attached:
            merged["existing_documents"] = self.documents_attached

        if self.rag_context and "rag_context" not in merged:
            merged["rag_context"] = self.rag_context

        for k, v in self.auto_params.items():
            if k not in merged or merged[k] is None:
                merged[k] = v

        if self.warnings:
            existing = merged.get("ingestion_warnings") or []
            merged["ingestion_warnings"] = existing + self.warnings

        return merged


async def ingest_for_task(
    task_type: str,
    organization_id: str,
    project_id: str | None,
    input_params: dict[str, Any],
) -> IngestionResult:
    """Point d'entrée principal : enrichit les params d'une tâche."""
    result = IngestionResult()

    if not project_id:
        return result

    reqs = TASK_DOCUMENT_REQUIREMENTS.get(task_type)
    if not reqs:
        return result

    from app.database import get_supabase_admin
    admin = get_supabase_admin()

    # 1. Récupérer les documents du projet filtrés par type + keywords
    matched_docs = _match_project_documents(
        admin=admin,
        org_id=organization_id,
        project_id=project_id,
        required_types=reqs["required_types"],
        keywords=reqs["keywords"],
        max_documents=reqs["max_documents"],
    )
    result.documents_attached = matched_docs

    if not matched_docs and reqs["max_documents"] > 0 and reqs["required_types"]:
        result.warnings.append(
            f"Aucun document trouvé dans le projet pour task_type={task_type} "
            f"(types attendus : {', '.join(reqs['required_types'])})"
        )

    # 2. Cas spécifiques : certaines tâches attendent un document précis
    result = await _enrich_task_specific(task_type, input_params, result, admin, organization_id)

    # 3. RAG via pgvector (si applicable)
    if reqs["keywords"] and matched_docs:
        try:
            from app.agent.rag import build_project_context
            query = " ".join(reqs["keywords"][:5])
            result.rag_context = await build_project_context(
                query=query,
                organization_id=organization_id,
                project_id=project_id,
                top_k=6,
                max_chars=6000,
            )
        except Exception as exc:
            result.warnings.append(f"RAG échoué : {exc}")

    return result


def _match_project_documents(
    admin: Any,
    org_id: str,
    project_id: str,
    required_types: list[str],
    keywords: list[str],
    max_documents: int,
) -> list[dict[str, Any]]:
    """Matching déterministe des documents du projet.

    Priorité : file_type match → keyword match dans filename → ordre de création décroissant.
    """
    if max_documents <= 0:
        return []

    try:
        result = admin.table("documents").select(
            "id, filename, file_type, created_at, processed, size_bytes"
        ).eq("project_id", project_id).eq("organization_id", org_id).order(
            "created_at", desc=True,
        ).limit(200).execute()
    except Exception as exc:
        logger.warning("Query documents échec : %s", exc)
        return []

    docs = result.data or []

    # Filtrage par type si requis
    if required_types:
        docs = [d for d in docs if (d.get("file_type") or "").lower() in required_types]

    # Scoring par mots-clés
    if keywords:
        for d in docs:
            name = (d.get("filename") or "").lower()
            score = sum(1 for kw in keywords if kw in name)
            d["_score"] = score
        docs.sort(key=lambda d: (-(d.get("_score", 0)), d.get("created_at") or ""), reverse=False)

    return docs[:max_documents]


async def _enrich_task_specific(
    task_type: str,
    input_params: dict[str, Any],
    result: IngestionResult,
    admin: Any,
    organization_id: str,
) -> IngestionResult:
    """Logique spécifique à certaines tâches : chargement auto de docs particuliers."""

    # reponse_observations_autorite : récupère le texte du PDF courrier
    if task_type == "reponse_observations_autorite":
        doc_id = input_params.get("autorite_pdf_document_id")
        if doc_id:
            pdf_text = _extract_pdf_text(admin, organization_id, doc_id, result)
            if pdf_text:
                result.auto_params["autorite_pdf_text"] = pdf_text[:20000]

    # idc_geneve_rapport : extraction auto des factures PDF marquées
    if task_type == "idc_geneve_rapport":
        if not input_params.get("invoice_document_ids"):
            invoice_ids = [
                d["id"] for d in result.documents_attached
                if any(kw in (d.get("filename") or "").lower()
                       for kw in ["facture", "mazout", "gaz", "chauffage"])
            ]
            if invoice_ids:
                result.auto_params["invoice_document_ids"] = invoice_ids

    # metres_automatiques_ifc : si pas de doc explicite, prendre le 1er IFC du projet
    if task_type == "metres_automatiques_ifc":
        if not input_params.get("ifc_document_id"):
            ifc_docs = [d for d in result.documents_attached if d.get("file_type") == "ifc"]
            if ifc_docs:
                result.auto_params["ifc_document_id"] = ifc_docs[0]["id"]
                result.warnings.append(
                    f"IFC auto-sélectionné : {ifc_docs[0]['filename']}"
                )

    # dossier_mise_enquete : structure les docs pour matching pièces attendues
    if task_type == "dossier_mise_enquete":
        existing = [
            {
                "id": d["id"],
                "filename": d["filename"],
                "file_type": d["file_type"],
            }
            for d in result.documents_attached
        ]
        result.auto_params["existing_documents"] = existing

    return result


def _extract_pdf_text(
    admin: Any,
    organization_id: str,
    doc_id: str,
    result: IngestionResult,
) -> str | None:
    """Télécharge un PDF depuis storage et extrait son texte."""
    try:
        doc = admin.table("documents").select("storage_path, filename").eq(
            "id", doc_id,
        ).eq("organization_id", organization_id).maybe_single().execute()
        if not doc.data:
            result.warnings.append(f"Document {doc_id} introuvable pour extraction texte")
            return None

        from app.database import get_storage
        storage = get_storage()
        pdf_bytes = storage.download(doc.data["storage_path"])

        from app.services.pdf_extractor import extract_text_from_pdf
        text, _ = extract_text_from_pdf(pdf_bytes)
        return text
    except Exception as exc:
        result.warnings.append(f"Extraction PDF {doc_id} échouée : {exc}")
        return None
