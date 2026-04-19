"""Modèles User."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

UserRole = Literal["admin", "member", "viewer"]


class UserBase(BaseModel):
    full_name: Optional[str] = Field(None, max_length=200)


class UserCreate(UserBase):
    email: EmailStr
    password: str = Field(..., min_length=8)
    organization_name: Optional[str] = None
    # V2 - contexte Suisse
    country: Optional[Literal["CH", "FR"]] = "CH"
    canton: Optional[str] = None
    language: Optional[Literal["fr", "de", "it", "en"]] = "fr"
    currency: Optional[Literal["CHF", "EUR"]] = "CHF"
    vat_number: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None


class User(UserBase):
    id: str
    organization_id: str
    role: UserRole
    created_at: datetime


class UserInvite(BaseModel):
    email: EmailStr
    role: UserRole = "member"
