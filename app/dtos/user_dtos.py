from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class CreateUserDTO(BaseModel):
    organization_id: int = Field(..., gt=0)
    role_id: int = Field(..., gt=0)
    email: EmailStr
    full_name: str | None = None
    avatar_url: str | None = None
    provider_id: str
    email_verified: bool = False
    status: str
    joined_at: datetime
    last_login_at: datetime


class UpdateUserDTO(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None
    email_verified: bool | None = None
    status: str | None = None
    provider_id: str | None = None
    joined_at: datetime | None = None
    last_login_at: datetime | None = None
