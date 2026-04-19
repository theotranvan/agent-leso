"""Modèles Pydantic pour AEAI checklists."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


BuildingType = Literal[
    "habitation_faible", "habitation_moyenne", "habitation_elevee",
    "administration_faible", "administration_moyenne", "administration_elevee",
    "ecole", "erp_petit", "erp_moyen", "erp_grand",
    "parking_souterrain", "industriel", "depot", "hopital",
]

HeightClass = Literal["faible_<11m", "moyenne_11-30m", "elevee_>30m"]

ChecklistItemStatus = Literal["A_VERIFIER", "CONFORME", "NON_CONFORME", "NON_APPLICABLE"]


class AEAIChecklistItem(BaseModel):
    id: str
    reference: str
    title: str
    description: Optional[str] = None
    status: ChecklistItemStatus = "A_VERIFIER"
    severity: Literal["BLOQUANT", "IMPORTANT", "INFO"] = "IMPORTANT"
    notes: Optional[str] = None


class AEAIChecklistCreate(BaseModel):
    project_id: Optional[str] = None
    building_type: BuildingType
    height_class: Optional[HeightClass] = None
    height_m: Optional[float] = None
    nb_occupants_max: Optional[int] = None


class AEAIChecklistUpdate(BaseModel):
    items: list[AEAIChecklistItem] = Field(default_factory=list)
    status: Optional[Literal["draft", "completed", "validated"]] = None
