"""Vector store via pgvector - stockage et recherche sémantique multi-tenant."""
import logging
from typing import Any, Optional

from app.database import get_supabase_admin
from app.services.embeddings import embed_query

logger = logging.getLogger(__name__)


async def store_chunks(
    document_id: str,
    organization_id: str,
    project_id: Optional[str],
    chunks: list[str],
    embeddings: list[list[float]],
    metadata_base: Optional[dict] = None,
) -> int:
    """Stocke des chunks + embeddings dans document_embeddings.
    Retourne le nombre de chunks insérés.
    """
    if len(chunks) != len(embeddings):
        raise ValueError("chunks et embeddings doivent avoir la même longueur")

    admin = get_supabase_admin()
    rows = []
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        rows.append({
            "document_id": document_id,
            "organization_id": organization_id,
            "project_id": project_id,
            "chunk_index": idx,
            "chunk_text": chunk,
            "embedding": embedding,
            "metadata": metadata_base or {},
        })

    # Insert par batch de 100 pour éviter les payloads trop lourds
    inserted = 0
    for i in range(0, len(rows), 100):
        batch = rows[i:i + 100]
        try:
            admin.table("document_embeddings").insert(batch).execute()
            inserted += len(batch)
        except Exception as e:
            logger.error(f"Erreur insert embeddings batch {i}: {e}")
    return inserted


async def search_similar(
    query: str,
    organization_id: str,
    project_id: Optional[str] = None,
    top_k: int = 8,
    similarity_threshold: float = 0.3,
) -> list[dict[str, Any]]:
    """Recherche sémantique multi-tenant via pgvector.

    Utilise la fonction SQL match_embeddings (créée par la migration).
    Filtre STRICTEMENT par organization_id pour garantir l'isolation.
    """
    query_embedding = await embed_query(query)
    admin = get_supabase_admin()

    try:
        result = admin.rpc(
            "match_embeddings",
            {
                "query_embedding": query_embedding,
                "match_organization_id": organization_id,
                "match_project_id": project_id,
                "match_threshold": similarity_threshold,
                "match_count": top_k,
            },
        ).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Erreur recherche vectorielle: {e}")
        return []


async def delete_document_embeddings(document_id: str) -> None:
    """Supprime tous les embeddings d'un document."""
    admin = get_supabase_admin()
    admin.table("document_embeddings").delete().eq("document_id", document_id).execute()
