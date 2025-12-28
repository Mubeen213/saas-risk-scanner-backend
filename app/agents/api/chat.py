import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agents.dependencies import get_chat_service
from app.agents.dtos.chat import ChatMessageDTO
from app.agents.schemas.chat import ChatMessageRequest
from app.agents.services.chat_service import ChatService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/")
async def chat(
    request: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    payload = ChatMessageDTO(
        organization_id=1,
        user_id=1,
        message=request.message,
        thread_id=request.thread_id,
    )

    return StreamingResponse(
        chat_service.stream_response(payload),
        media_type="text/event-stream",
    )
