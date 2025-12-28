from pydantic import BaseModel


class ChatMessageDTO(BaseModel):
    organization_id: int
    user_id: int
    message: str
    thread_id: str | None = None
