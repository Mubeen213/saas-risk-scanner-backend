from typing import Any

from pydantic import BaseModel


class PlanResponse(BaseModel):
    id: int
    name: str
    display_name: str
    max_users: int | None
    max_apps: int | None
