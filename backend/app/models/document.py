"""Modèles Document."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

FileType = Literal["pdf", "docx", "ifc", "bcf", "xlsx", "image"]


class DocumentBase(BaseModel):
    filename: str
    file_type: FileType


class DocumentCreate(DocumentBase):
    project_id: Optional[str] = None
    storage_path: str


class Document(DocumentBase):
    id: str
    organization_id: str
    project_id: Optional[str] = None
    storage_path: str
    extracted_text: Optional[str] = None
    page_count: Optional[int] = None
    processed: bool = False
    created_at: datetime
