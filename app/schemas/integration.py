from datetime import datetime

from pydantic import BaseModel, Field


class IntegrationConnectRequest(BaseModel):
    provider_slug: str = Field(
        ..., description="Provider slug (e.g., 'google-workspace')"
    )
    redirect_uri: str | None = Field(
        None,
        description="Redirect URI after OAuth (optional, defaults to frontend callback)",
    )


class IntegrationConnectResponse(BaseModel):
    authorization_url: str
    state: str


class IntegrationCallbackRequest(BaseModel):
    provider_slug: str
    code: str
    state: str


class ConnectionResponse(BaseModel):
    id: int
    organization_id: int
    provider_id: int
    provider_slug: str | None = None
    status: str
    admin_email: str | None
    workspace_domain: str | None
    scopes_granted: list[str]
    last_sync_completed_at: datetime | None
    last_sync_status: str | None
    created_at: datetime
    updated_at: datetime


class ConnectionListResponse(BaseModel):
    connections: list[ConnectionResponse]


class SyncRequest(BaseModel):
    connection_id: int


class SyncResponse(BaseModel):
    connection_id: int
    status: str
    message: str


class DisconnectResponse(BaseModel):
    success: bool
    message: str
