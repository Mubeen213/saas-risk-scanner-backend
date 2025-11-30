from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateDiscoveredAppDTO(BaseModel):
    organization_id: int = Field(..., gt=0)
    connection_id: int = Field(..., gt=0)
    client_id: str
    display_name: str | None = None
    product_id: int | None = None
    client_type: str | None = None
    status: str = "active"
    first_seen_at: datetime
    last_seen_at: datetime
    all_scopes: list[str] = Field(default_factory=list)
    raw_data: dict[str, Any] = Field(default_factory=dict)


class UpdateDiscoveredAppDTO(BaseModel):
    display_name: str | None = None
    product_id: int | None = None
    client_type: str | None = None
    status: str | None = None
    last_seen_at: datetime | None = None
    all_scopes: list[str] | None = None
    raw_data: dict[str, Any] | None = None


class CreateAppAuthorizationDTO(BaseModel):
    discovered_app_id: int = Field(..., gt=0)
    workspace_user_id: int = Field(..., gt=0)
    scopes: list[str] = Field(default_factory=list)
    status: str = "active"
    authorized_at: datetime
    raw_data: dict[str, Any] = Field(default_factory=dict)


class UpdateAppAuthorizationDTO(BaseModel):
    scopes: list[str] | None = None
    status: str | None = None
    revoked_at: datetime | None = None
    raw_data: dict[str, Any] | None = None
