from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    role_id: int
    email: EmailStr
    full_name: str | None = None
    avatar_url: str | None = None
    provider_id: str | None = None
    email_verified: bool = False
    status: str
    invited_by_user_id: int | None = None
    invited_at: datetime | None = None
    joined_at: datetime | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
