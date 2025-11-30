from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DiscoveredApp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    connection_id: int
    client_id: str
    display_name: str | None = None
    product_id: int | None = None
    client_type: str | None = None
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    all_scopes: list[str] = Field(default_factory=list)
    raw_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
