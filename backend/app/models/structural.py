"""Modèles Pydantic pour structure / SAF."""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class StructuralNode(BaseModel):
    id: str
    x: float
    y: float
    z: float


class StructuralMember(BaseModel):
    id: str
    type: Literal["beam", "girder", "column", "post", "brace", "tie"] = "beam"
    node_start: str
    node_end: str
    section: str  # clé CrossSection
    material: str  # clé Material
    length_m: Optional[float] = None  # recalculé si absent


class StructuralSupport(BaseModel):
    id: str
    node: str
    type: Literal["fixed", "pinned", "roller"] = "pinned"


class StructuralLoadCase(BaseModel):
    id: str
    name: str
    category: Literal["Permanent", "Variable", "Accidentel", "Sismique"] = "Variable"
    group: Optional[str] = "Main"


class StructuralLoad(BaseModel):
    id: str
    case: str
    target: str
    target_type: Literal["member", "node", "surface"] = "member"
    type: Literal["uniform_vertical", "point_vertical", "moment", "horizontal"] = "uniform_vertical"
    direction: Literal["X", "Y", "Z", "-Z"] = "-Z"
    value_kN_m: Optional[float] = None
    value_kN: Optional[float] = None


class StructuralCombinationFactor(BaseModel):
    case: str
    factor: float


class StructuralCombination(BaseModel):
    id: str
    name: str
    type: Literal["linear_add", "envelope"] = "linear_add"
    factors: list[StructuralCombinationFactor] = Field(default_factory=list)


class StructuralProjectInfo(BaseModel):
    name: str
    referentiel: Literal["sia", "eurocode"] = "sia"
    country: str = "CH"
    exposure_class: str = "XC2"
    consequence_class: Literal["CC1", "CC2", "CC3"] = "CC2"
    seismic_zone: Literal["Z1a", "Z1b", "Z2", "Z3a", "Z3b"] = "Z1b"


class StructuralModelInput(BaseModel):
    name: str
    project_id: Optional[str] = None
    material_default: Optional[str] = None
    project: StructuralProjectInfo
    nodes: list[StructuralNode] = Field(default_factory=list)
    members: list[StructuralMember] = Field(default_factory=list)
    supports: list[StructuralSupport] = Field(default_factory=list)
    load_cases: list[StructuralLoadCase] = Field(default_factory=list)
    loads: list[StructuralLoad] = Field(default_factory=list)
    combinations: list[StructuralCombination] = Field(default_factory=list)


class StructuralSafGenerateRequest(BaseModel):
    model_id: str


class StructuralImportResultsRequest(BaseModel):
    model_id: str
    author_name: Optional[str] = None
