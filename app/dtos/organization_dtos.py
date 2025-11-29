from pydantic import BaseModel, Field


class CreateOrganizationDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    domain: str = Field(..., min_length=1, max_length=255)
    plan_id: int = Field(..., gt=0)
    status: str
