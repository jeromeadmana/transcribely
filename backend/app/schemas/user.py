from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional
import re
from app.models.user import MemberRole


# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UserWithOrg(UserResponse):
    current_organization_id: Optional[UUID] = None
    current_organization_name: Optional[str] = None
    role: Optional[MemberRole] = None


# Auth schemas
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Organization schemas
class OrganizationCreate(BaseModel):
    name: str


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    plan: str
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationMemberResponse(BaseModel):
    user_id: UUID
    organization_id: UUID
    role: MemberRole
    joined_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True
