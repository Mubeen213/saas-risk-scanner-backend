from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.agents.chat_agent import get_chat_agent
import json

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


async def stream_sse(message: str, thread_id: str):
    """Stream Server-Sent Events to client."""
    agent = get_chat_agent()
    async for event in agent.stream_events(message, thread_id):
        data = {"type": event.type.value, "data": event.data}
        yield f"data: {json.dumps(data)}\n\n"


@router.post("/")
async def chat(request: ChatRequest):
    return StreamingResponse(
        stream_sse(request.message, request.thread_id or "default"),
        media_type="text/event-stream",
    )


@router.post("/run")
async def chat_run(request: ChatRequest):
    response = await get_chat_agent().run(request.message, request.thread_id or "default")
    return {"response": response}
