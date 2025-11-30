from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProductAuthConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None = None
    identity_provider_id: int
    auth_type: str
    client_id: str | None = None
    client_secret: str | None = None
    authorization_url: str | None = None
    token_url: str | None = None
    userinfo_url: str | None = None
    revoke_url: str | None = None
    scopes: list[str] = Field(default_factory=list)
    redirect_uri: str | None = None
    additional_params: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
