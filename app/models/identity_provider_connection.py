from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IdentityProviderConnection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    identity_provider_id: int
    connected_by_user_id: int
    status: str
    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    scopes_granted: list[str] = Field(default_factory=list)
    admin_email: str | None = None
    workspace_domain: str | None = None

    last_token_refresh_at: datetime | None = None
    token_refresh_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
