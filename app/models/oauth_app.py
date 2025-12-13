from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OAuthApp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    connection_id: int

    client_id: str
    name: str

    risk_score: int = 0
    is_system_app: bool = False
    is_trusted: bool = False

    scopes_summary: list[str] = Field(default_factory=list)
    image_url: str | None = None

    raw_data: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime
