from langgraph.types import Command

from app.agents.core.logging import AgentLogger


class InterruptHandler:
    def __init__(self, graph):
        self._graph = graph
        self._logger = AgentLogger("interrupt_handler")

    async def approve(self, thread_id: str, data: dict | None = None) -> dict:
        self._logger.log_interrupt("resume_approved", {"thread_id": thread_id})
        config = {"configurable": {"thread_id": thread_id}}
        resume_value = data if data else True
        return await self._graph.ainvoke(Command(resume=resume_value), config)

    async def reject(self, thread_id: str, reason: str | None = None) -> dict:
        self._logger.log_interrupt("resume_rejected", {"thread_id": thread_id, "reason": reason})
        config = {"configurable": {"thread_id": thread_id}}
        return await self._graph.ainvoke(Command(resume=False), config)

    async def get_pending(self, thread_id: str) -> dict | None:
        config = {"configurable": {"thread_id": thread_id}}
        state = await self._graph.aget_state(config)
        return state.values.get("__interrupt__") if state else None
