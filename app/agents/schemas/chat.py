from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    message: str
    thread_id: str | None = None
