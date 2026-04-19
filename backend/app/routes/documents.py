"""Routes documents - upload, pipeline RAG, téléchargement URLs signées."""
import logging
import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile

from app.config import settings
from app.database import get_storage, get_supabase_admin
from app.middleware import AuthUser, audit_log, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


EXT_TO_TYPE = {
    "pdf": "pdf",
    "docx": "docx",
    "ifc": "ifc",
    "bcf": "bcf",
    "xlsx": "xlsx",
    "xls": "xlsx",
    "png": "image",
    "jpg": "image",
    "jpeg": "image",
    "tiff": "image",
}


@router.post("/upload", status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    user: Annotated[AuthUser, Depends(get_current_user)],
    request: Request,
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
):
    """Upload un document et déclenche le pipeline d'extraction + embedding en background."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    # Validation extension
    filename = file.filename or "document"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Extension {ext} non autorisée")

    file_type = EXT_TO_TYPE.get(ext, "pdf")

    # Lecture et validation taille
    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"Fichier trop volumineux ({size_mb:.1f} MB > {settings.MAX_UPLOAD_SIZE_MB} MB)")

    # Upload storage
    storage = get_storage()
    doc_id = str(uuid.uuid4())
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    storage_path = f"{user.organization_id}/uploads/{doc_id}/{safe_filename}"
    storage.upload(storage_path, file_bytes, content_type=file.content_type or "application/octet-stream")

    # Insert DB
    admin = get_supabase_admin()
    doc = admin.table("documents").insert({
        "id": doc_id,
        "organization_id": user.organization_id,
        "project_id": project_id,
        "filename": safe_filename,
        "file_type": file_type,
        "storage_path": storage_path,
        "processed": False,
    }).execute()

    await audit_log(
        action="document_uploaded",
        organization_id=user.organization_id,
        user_id=user.id,
        resource_type="document",
        resource_id=doc_id,
        metadata={"filename": safe_filename, "size_mb": round(size_mb, 2)},
        ip_address=request.client.host if request.client else None,
    )

    # Pipeline en background (extraction + embeddings)
    background_tasks.add_task(_process_document_pipeline, doc_id, user.organization_id, project_id)

    return doc.data[0] if doc.data else {"id": doc_id, "filename": safe_filename}


async def _process_document_pipeline(document_id: str, organization_id: str, project_id: Optional[str]):
    """Pipeline complet : download → extract → chunk → embed → store."""
    try:
        from app.services.embeddings import chunk_text, generate_embeddings
        from app.services.ifc_parser import parse_ifc_metadata
        from app.services.ocr import ocr_pdf_scanned
        from app.services.pdf_extractor import extract_text_from_pdf, is_scanned_pdf
        from app.services.vector_store import store_chunks

        admin = get_supabase_admin()
        storage = get_storage()

        doc = admin.table("documents").select("*").eq("id", document_id).maybe_single().execute()
        if not doc.data:
            return

        file_bytes = storage.download(doc.data["storage_path"])
        file_type = doc.data["file_type"]
        extracted_text = ""
        page_count = None

        if file_type == "pdf":
            text, page_count = extract_text_from_pdf(file_bytes)
            if is_scanned_pdf(file_bytes):
                logger.info(f"PDF scanné détecté {document_id}, OCR en cours")
                text = ocr_pdf_scanned(file_bytes)
            extracted_text = text

        elif file_type == "docx":
            try:
                import docx
                from io import BytesIO
                d = docx.Document(BytesIO(file_bytes))
                extracted_text = "\n\n".join(p.text for p in d.paragraphs if p.text.strip())
            except Exception as e:
                logger.error(f"Erreur extraction docx: {e}")

        elif file_type == "ifc":
            metadata = parse_ifc_metadata(file_bytes)
            extracted_text = f"Métadonnées IFC: {metadata}"

        elif file_type == "image":
            from app.services.ocr import ocr_image
            extracted_text = ocr_image(file_bytes)

        # Update document
        admin.table("documents").update({
            "extracted_text": extracted_text[:100000],  # cap à 100k chars
            "page_count": page_count,
        }).eq("id", document_id).execute()

        # Chunking + embeddings (seulement si texte)
        if extracted_text and len(extracted_text.strip()) > 50:
            chunks = chunk_text(extracted_text)
            if chunks:
                embeddings = await generate_embeddings(chunks)
                await store_chunks(
                    document_id=document_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    chunks=chunks,
                    embeddings=embeddings,
                    metadata_base={"filename": doc.data["filename"]},
                )
                logger.info(f"Document {document_id}: {len(chunks)} chunks embarqués")

        admin.table("documents").update({"processed": True}).eq("id", document_id).execute()

    except Exception as e:
        logger.exception(f"Pipeline document {document_id} échoué: {e}")


@router.get("")
async def list_documents(
    user: Annotated[AuthUser, Depends(get_current_user)],
    project_id: Optional[str] = None,
    limit: int = 100,
):
    admin = get_supabase_admin()
    query = admin.table("documents").select("*").eq("organization_id", user.organization_id)
    if project_id:
        query = query.eq("project_id", project_id)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return {"documents": result.data or []}


@router.get("/{document_id}")
async def get_document(document_id: str, user: Annotated[AuthUser, Depends(get_current_user)]):
    admin = get_supabase_admin()
    doc = admin.table("documents").select("*").eq("id", document_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not doc.data:
        raise HTTPException(status_code=404, detail="Document introuvable")

    storage = get_storage()
    try:
        signed_url = storage.get_signed_url(doc.data["storage_path"], expires_in=3600)
    except Exception as e:
        logger.error(f"Erreur URL signée: {e}")
        signed_url = None

    return {**doc.data, "signed_url": signed_url}


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    request: Request,
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    doc = admin.table("documents").select("*").eq("id", document_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not doc.data:
        raise HTTPException(status_code=404, detail="Document introuvable")

    # Suppression storage
    try:
        get_storage().delete(doc.data["storage_path"])
    except Exception as e:
        logger.warning(f"Erreur suppression storage: {e}")

    # DB (embeddings cascade)
    admin.table("documents").delete().eq("id", document_id).execute()

    await audit_log(
        action="document_deleted",
        organization_id=user.organization_id,
        user_id=user.id,
        resource_type="document",
        resource_id=document_id,
        ip_address=request.client.host if request.client else None,
    )
    return None
