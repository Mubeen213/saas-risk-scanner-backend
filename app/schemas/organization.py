from pydantic import BaseModel

from app.schemas.plan import PlanResponse


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    domain: str | None
    logo_url: str | None
    status: str
    plan: PlanResponse
