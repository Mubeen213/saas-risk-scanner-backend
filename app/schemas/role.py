from pydantic import BaseModel


class RoleResponse(BaseModel):
    id: int
    name: str
    display_name: str
