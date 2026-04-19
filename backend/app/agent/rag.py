"""RAG (Retrieval-Augmented Generation) pour l'agent.

Récupère le contexte pertinent depuis les documents du projet via pgvector,
puis construit le prompt contextualisé.
"""
import logging
from typing import Optional

from app.services.vector_store import search_similar

logger = logging.getLogger(__name__)


async def build_project_context(
    query: str,
    organization_id: str,
    project_id: Optional[str] = None,
    top_k: int = 6,
    max_chars: int = 8000,
) -> str:
    """Construit un bloc de contexte à partir des documents du projet.

    Retourne une string formatée à injecter dans le prompt utilisateur.
    """
    results = await search_similar(
        query=query,
        organization_id=organization_id,
        project_id=project_id,
        top_k=top_k,
    )

    if not results:
        return ""

    chunks_formatted = []
    total_chars = 0
    for idx, r in enumerate(results, 1):
        chunk = r.get("chunk_text", "")
        similarity = r.get("similarity", 0)
        if total_chars + len(chunk) > max_chars:
            # Tronque le dernier chunk pour tenir dans la limite
            remaining = max_chars - total_chars
            if remaining > 200:
                chunk = chunk[:remaining] + "..."
                chunks_formatted.append(f"[Extrait {idx} | similarité {similarity:.2f}]\n{chunk}")
            break
        chunks_formatted.append(f"[Extrait {idx} | similarité {similarity:.2f}]\n{chunk}")
        total_chars += len(chunk)

    context_block = "\n\n---\n\n".join(chunks_formatted)
    return f"""CONTEXTE DU PROJET (extraits des documents uploadés) :

{context_block}

---
"""


async def get_project_summary(organization_id: str, project_id: str) -> dict:
    """Récupère les informations de synthèse d'un projet."""
    from app.database import get_supabase_admin

    admin = get_supabase_admin()
    project = admin.table("projects").select("*").eq("id", project_id).maybe_single().execute()

    if not project.data:
        return {}

    # Nb documents et nb chunks
    docs = admin.table("documents").select("id", count="exact").eq("project_id", project_id).execute()
    chunks = admin.table("document_embeddings").select("id", count="exact").eq("project_id", project_id).execute()

    return {
        **project.data,
        "nb_documents": docs.count or 0,
        "nb_chunks": chunks.count or 0,
    }
