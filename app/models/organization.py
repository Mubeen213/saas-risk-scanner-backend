from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Organization(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    domain: str | None = None
    logo_url: str | None = None
    plan_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
