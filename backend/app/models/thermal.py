"""Modèles Pydantic pour le module thermique."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ThermalZone(BaseModel):
    id: Optional[str] = None
    name: str
    affectation: str = "logement_collectif"
    area: float = Field(gt=0)
    volume: Optional[float] = None
    temp_setpoint: float = 20.0


class WallLayer(BaseModel):
    material: str
    thickness: float = Field(gt=0, description="Épaisseur en m")
    lambda_: Optional[float] = Field(None, alias="lambda", description="W/m·K - surcharge le lambda catalogue si fourni")


class Wall(BaseModel):
    id: Optional[str] = None
    type: str = "mur_exterieur"
    orientation: Optional[str] = None  # N/S/E/W/horizontal
    area: float = Field(gt=0)
    u_value: Optional[float] = None
    layers: list[WallLayer] = Field(default_factory=list)


class Opening(BaseModel):
    id: Optional[str] = None
    type: str = "fenetre"  # fenetre | porte_vitree | porte_opaque
    area: float = Field(gt=0)
    u_value: Optional[float] = None
    g_value: Optional[float] = None
    orientation: Optional[str] = None


class ThermalBridge(BaseModel):
    type: str
    length: float = Field(gt=0)
    psi: float  # W/m·K


class ThermalSystems(BaseModel):
    heating: Optional[dict] = None       # {vector, efficiency, temp_flow, temp_return}
    ventilation: Optional[dict] = None   # {type, heat_recovery_pct}
    ecs: Optional[dict] = None           # {vector, storage_liters}
    cooling: Optional[dict] = None


class ThermalModelInput(BaseModel):
    name: str
    project_id: Optional[str] = None
    canton: str
    affectation: str
    operation_type: Literal["neuf", "renovation", "transformation"] = "neuf"
    standard: str = "sia_380_1"
    climate: Optional[dict] = None  # si vide, auto-déduit depuis canton
    zones: list[ThermalZone] = Field(default_factory=list)
    walls: list[Wall] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)
    thermal_bridges: list[ThermalBridge] = Field(default_factory=list)
    systems: ThermalSystems = Field(default_factory=ThermalSystems)
    hypotheses: dict = Field(default_factory=dict)


class ThermalRunRequest(BaseModel):
    model_id: str
    engine: Literal["lesosai_stub", "lesosai_file", "gbxml", "stub"] = "lesosai_stub"
    generate_justificatif: bool = True
    author_name: Optional[str] = None


class ThermalImportResultsRequest(BaseModel):
    model_id: str
    # Le PDF Lesosai est uploadé via multipart, pas ici
