"""Modèles Pydantic pour pré-BIM."""
from typing import Optional

from pydantic import BaseModel, Field


class StoreySpec(BaseModel):
    name: str
    elevation_m: float = 0
    height_m: float = Field(gt=0, default=2.8)
    area_m2: float = Field(gt=0)
    usage: str = "logement_collectif"


class EnvelopeSpec(BaseModel):
    plan_width_m: float = Field(gt=0, default=20)
    plan_depth_m: float = Field(gt=0, default=10)
    wall_composition_key: str = "mur_ext_neuf_standard"
    roof_composition_key: str = "toit_neuf_perform"
    slab_ground_composition_key: str = "dalle_sur_terrain_neuf"
    window_ratio_by_orientation: dict[str, float] = Field(
        default_factory=lambda: {"N": 0.15, "S": 0.30, "E": 0.25, "W": 0.25}
    )
    window_u_value: float = 1.0
    window_g_value: float = 0.55


class PreBIMSpec(BaseModel):
    project_name: str
    building_name: str = "Bâtiment A"
    site_name: str = "Site"
    canton: str
    operation_type: str = "neuf"
    affectation: str = "logement_collectif"
    nb_logements: Optional[int] = None
    storeys: list[StoreySpec]
    envelope: EnvelopeSpec = Field(default_factory=EnvelopeSpec)
    assumptions: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)


class PreBIMFromTextRequest(BaseModel):
    program_text: str
    project_id: Optional[str] = None
    hints: dict = Field(default_factory=dict)


class PreBIMFromSpecRequest(BaseModel):
    spec: PreBIMSpec
    project_id: Optional[str] = None
