from typing import AsyncGenerator
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.core.logging import AgentLogger
import logging


class AgentExecutor:
    def __init__(self, graph, name: str = "executor"):
        self._graph = graph
        self._logger = AgentLogger(name)

    async def run(
        self,
        message: str,
        thread_id: str,
        context: dict | None = None,
    ) -> dict:
        self._logger.log_llm_start(
            prompt_preview=message[:100],
            message_count=1,
        )
        
        config = {"configurable": {"thread_id": thread_id}}
        initial = {
            "messages": [HumanMessage(content=message)],
            **(context or {}),
        }
        
        result = await self._graph.ainvoke(initial, config)
        
        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            usage = getattr(last, "usage_metadata", {}) or {}
            self._logger.log_llm_end(
                response_preview=str(last.content)[:150] if hasattr(last, "content") else "",
                usage={
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            )
        
        return result

    async def stream(
        self,
        message: str,
        thread_id: str,
    ) -> AsyncGenerator[str, None]:
        config = {"configurable": {"thread_id": thread_id}}
        initial = {"messages": [HumanMessage(content=message)]}
        logging.info("Streaming started")
        async for event in self._graph.astream_events(initial, config=config, version="v2"):
            logging.info("Event received")
            if event.get("event") == "on_chat_model_stream":
                logging.info("Chat model stream event received")
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content"):
                    logging.info("Chunk received")
                    yield self._extract_text(chunk.content)

    def _extract_text(self, content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        return ""

    def get_response_text(self, result: dict) -> str:
        messages = result.get("messages", [])
        if messages and isinstance(messages[-1], AIMessage):
            return str(messages[-1].content)
        return ""
