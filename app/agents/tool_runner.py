import time
import logging
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


class ToolRunner:
    """Reusable tool executor with logging."""
    
    def __init__(self, tools: list):
        self._node = ToolNode(tools)

    async def run(self, state: dict, config: RunnableConfig | None = None) -> dict:
        messages = state.get("messages", [])
        last = messages[-1] if messages else None
        
        if not last or not getattr(last, "tool_calls", None):
            return {"messages": []}

        for tc in last.tool_calls:
            logger.info(f"Tool: {tc['name']} args={tc.get('args', {})}")

        start = time.time()
        try:
            result = await self._node.ainvoke(state, config)
            logger.info(f"Tools done: {(time.time() - start)*1000:.0f}ms")
            return result
        except Exception as e:
            logger.error(f"Tool error: {e}")
            raise
