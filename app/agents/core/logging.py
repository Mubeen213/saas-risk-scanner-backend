import logging
from typing import Any
from datetime import datetime, timezone


class AgentLogger:
    def __init__(self, agent_name: str):
        self._name = agent_name
        self._logger = logging.getLogger(f"agents.{agent_name}")

    def log_llm_start(self, prompt_preview: str, message_count: int):
        self._logger.info(
            "LLM invocation started",
            extra={
                "agent": self._name,
                "event": "llm_start",
                "message_count": message_count,
                "prompt_preview": prompt_preview[:100],
                "timestamp": self._now(),
            },
        )

    def log_llm_end(self, response_preview: str, usage: dict[str, int]):
        self._logger.info(
            "LLM invocation completed",
            extra={
                "agent": self._name,
                "event": "llm_end",
                "response_preview": response_preview[:150],
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "timestamp": self._now(),
            },
        )

    def log_tool_start(self, tool_name: str, args: dict[str, Any]):
        self._logger.info(
            f"Tool execution started: {tool_name}",
            extra={
                "agent": self._name,
                "event": "tool_start",
                "tool_name": tool_name,
                "args": args,
                "timestamp": self._now(),
            },
        )

    def log_tool_end(self, tool_name: str, result_preview: str, duration_ms: float):
        self._logger.info(
            f"Tool execution completed: {tool_name}",
            extra={
                "agent": self._name,
                "event": "tool_end",
                "tool_name": tool_name,
                "result_preview": result_preview[:200],
                "duration_ms": round(duration_ms, 2),
                "timestamp": self._now(),
            },
        )

    def log_interrupt(self, interrupt_type: str, details: dict[str, Any]):
        self._logger.info(
            f"Interrupt: {interrupt_type}",
            extra={
                "agent": self._name,
                "event": "interrupt",
                "interrupt_type": interrupt_type,
                "details": details,
                "timestamp": self._now(),
            },
        )

    def log_structured_output(self, schema_name: str, fields: list[str]):
        self._logger.info(
            f"Structured output: {schema_name}",
            extra={
                "agent": self._name,
                "event": "structured_output",
                "schema": schema_name,
                "fields": fields,
                "timestamp": self._now(),
            },
        )

    def log_error(self, error_type: str, error_message: str):
        self._logger.error(
            f"Error: {error_type}",
            extra={
                "agent": self._name,
                "event": "error",
                "error_type": error_type,
                "error_message": error_message,
                "timestamp": self._now(),
            },
        )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
