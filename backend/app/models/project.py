"""Modèles Project."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ProjectStatus = Literal["active", "archived"]


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    type_ouvrage: Optional[str] = None
    address: Optional[str] = None
    lots: list[str] = Field(default_factory=list)
    normes_applicables: list[str] = Field(default_factory=list)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    type_ouvrage: Optional[str] = None
    address: Optional[str] = None
    lots: Optional[list[str]] = None
    normes_applicables: Optional[list[str]] = None
    status: Optional[ProjectStatus] = None


class Project(ProjectBase):
    id: str
    organization_id: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
