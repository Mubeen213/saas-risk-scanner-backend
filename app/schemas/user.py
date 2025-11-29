from datetime import datetime

from pydantic import BaseModel

from app.schemas.organization import OrganizationResponse
from app.schemas.role import RoleResponse


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    avatar_url: str | None
    email_verified: bool
    status: str
    last_login_at: datetime | None
    role: RoleResponse
    organization: OrganizationResponse
