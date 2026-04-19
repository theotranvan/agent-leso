"""Modèles Pydantic pour le module IDC Genève."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


VecteurType = Literal["gaz", "mazout", "chauffage_distance", "pac_air_eau",
                      "pac_sol_eau", "pellet", "buche", "electrique", "solaire_thermique"]


class IDCBuildingCreate(BaseModel):
    ega: Optional[str] = None
    address: str
    postal_code: Optional[str] = None
    sre_m2: float = Field(gt=0)
    heating_energy_vector: VecteurType
    building_year: Optional[int] = None
    nb_logements: Optional[int] = None
    regie_name: Optional[str] = None
    regie_email: Optional[EmailStr] = None
    project_id: Optional[str] = None


class IDCBuilding(IDCBuildingCreate):
    id: str
    organization_id: str
    created_at: datetime


class IDCInvoiceItem(BaseModel):
    value: float
    unit: str  # litres, m3, kwh, kg, etc.
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    source_document_id: Optional[str] = None


class IDCDeclarationCreate(BaseModel):
    building_id: str
    year: int = Field(ge=2015, le=2050)
    invoices: list[IDCInvoiceItem] = Field(default_factory=list)
    degree_days_period: Optional[float] = None
    notes: Optional[str] = None
