from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Plan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    display_name: str
    description: str | None = None
    max_users: int | None = None
    max_apps: int | None = None
    price_monthly_cents: int = 0
    price_yearly_cents: int = 0
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
