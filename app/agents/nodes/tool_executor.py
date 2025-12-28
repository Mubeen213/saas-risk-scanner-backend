import time
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage

from app.agents.core.logging import AgentLogger
import logging

class InstrumentedToolExecutor:
    def __init__(self, tools: list, name: str = "agent"):
        self._executor = ToolNode(tools)
        self._name = name
        self._logger = AgentLogger(name)

    async def invoke(self, state: dict, config: dict) -> dict:
        logging.info("Tool executor invoked")
        messages = state.get("messages", [])
        if not messages:
            return {"messages": []}

        last = messages[-1]
        if not hasattr(last, "tool_calls") or not last.tool_calls:
            return {"messages": []}

        for tool_call in last.tool_calls:
            self._logger.log_tool_start(
                tool_name=tool_call.get("name", "unknown"),
                args=self._sanitize_args(tool_call.get("args", {})),
            )

        start = time.time()
        try:
            result = await self._executor.ainvoke(state, config)
            elapsed_ms = (time.time() - start) * 1000

            for msg in result.get("messages", []):
                if isinstance(msg, ToolMessage):
                    self._logger.log_tool_end(
                        tool_name=msg.name or "unknown",
                        result_preview=str(msg.content)[:200],
                        duration_ms=elapsed_ms,
                    )

            return result
        except Exception as e:
            self._logger.log_error("tool_execution_failed", str(e))
            return {
                "messages": [
                    ToolMessage(
                        name=last.tool_calls[0].get("name", "unknown"),
                        tool_call_id=last.tool_calls[0].get("id", ""),
                        content=f"Tool execution failed: {str(e)[:100]}",
                    )
                ]
            }

    def _sanitize_args(self, args: dict) -> dict:
        sensitive_keys = {"password", "token", "secret", "api_key", "credential"}
        return {
            k: "[REDACTED]" if k.lower() in sensitive_keys else v
            for k, v in args.items()
        }
