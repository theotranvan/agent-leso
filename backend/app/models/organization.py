"""Modèles Organization."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

PlanType = Literal["starter", "pro", "enterprise"]


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    siret: Optional[str] = Field(None, max_length=20)
    email: EmailStr


class OrganizationCreate(OrganizationBase):
    plan: PlanType = "starter"


class Organization(OrganizationBase):
    id: str
    plan: PlanType
    tasks_used_this_month: int = 0
    tasks_limit: int = 500
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    active: bool = True
    created_at: datetime


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    siret: Optional[str] = None
    email: Optional[EmailStr] = None
