from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IdentityProvider(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    display_name: str
    description: str | None = None
    logo_url: str | None = None
    website_url: str | None = None
    documentation_url: str | None = None
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
