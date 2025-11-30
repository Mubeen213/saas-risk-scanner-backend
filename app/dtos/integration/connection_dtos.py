from datetime import datetime

from pydantic import BaseModel, Field


class CreateIdentityProviderConnectionDTO(BaseModel):
    organization_id: int = Field(..., gt=0)
    identity_provider_id: int = Field(..., gt=0)
    connected_by_user_id: int = Field(..., gt=0)
    status: str
    access_token_encrypted: str
    refresh_token_encrypted: str | None = None
    token_expires_at: datetime | None = None
    scopes_granted: list[str] = Field(default_factory=list)
    admin_email: str | None = None
    workspace_domain: str | None = None


class UpdateIdentityProviderConnectionDTO(BaseModel):
    status: str | None = None
    access_token_encrypted: str | None = None
    refresh_token_encrypted: str | None = None
    token_expires_at: datetime | None = None
    scopes_granted: list[str] | None = None
    last_sync_started_at: datetime | None = None
    last_sync_completed_at: datetime | None = None
    last_sync_status: str | None = None
    last_sync_error: str | None = None
    last_token_refresh_at: datetime | None = None
    token_refresh_count: int | None = None
    error_code: str | None = None
    error_message: str | None = None


class UpdateTokensDTO(BaseModel):
    access_token_encrypted: str
    refresh_token_encrypted: str | None = None
    token_expires_at: datetime | None = None


class MarkConnectionErrorDTO(BaseModel):
    status: str = "error"
    error_code: str
    error_message: str
