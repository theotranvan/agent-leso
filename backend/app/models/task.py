"""Modèles Task."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

TaskStatus = Literal["pending", "running", "completed", "failed"]
TaskType = Literal[
    # Opus 4.6 - critique
    "note_calcul_structure", "verification_eurocode",
    "calcul_thermique_re2020", "calcul_acoustique",
    # Sonnet 4.6 - standard
    "redaction_cctp", "memoire_technique", "chiffrage_dpgf", "chiffrage_dqe",
    "coordination_inter_lots", "dossier_permis_construire",
    "analyse_ifc", "doe_compilation",
    # Haiku 4.5 - léger
    "veille_reglementaire", "resume_document", "compte_rendu_reunion",
    "alerte_norme", "email_notification", "extraction_metadata",
]


class TaskCreate(BaseModel):
    task_type: TaskType
    project_id: Optional[str] = None
    input_params: dict = Field(default_factory=dict)
    send_email: bool = True
    recipient_emails: list[str] = Field(default_factory=list)


class Task(BaseModel):
    id: str
    organization_id: str
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    task_type: str
    status: TaskStatus
    model_used: Optional[str] = None
    input_params: dict = Field(default_factory=dict)
    result_url: Optional[str] = None
    result_preview: Optional[str] = None
    tokens_used: int = 0
    cost_euros: float = 0
    error_message: Optional[str] = None
    attempts: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None


class TaskStatusResponse(BaseModel):
    id: str
    status: TaskStatus
    progress: int = 0
    result_url: Optional[str] = None
    result_preview: Optional[str] = None
    error_message: Optional[str] = None
