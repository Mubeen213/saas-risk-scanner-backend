import logging
from typing import AsyncGenerator

from app.agents.dtos.chat import ChatMessageDTO
from app.agents.services.executor import AgentExecutor


logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, executor: AgentExecutor):
        self._executor = executor

    async def stream_response(
        self, payload: ChatMessageDTO
    ) -> AsyncGenerator[str, None]:
        thread_id = payload.thread_id or f"{payload.organization_id}_{payload.user_id}"

        logger.info(
            f"Starting agent invocation for thread={thread_id}, message={payload.message[:50]}..."
        )

        async for chunk in self._executor.stream(payload.message, thread_id):
            yield chunk

        logger.info(f"Agent invocation completed for thread={thread_id}")
