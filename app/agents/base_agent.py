from dataclasses import dataclass
from typing import AsyncGenerator
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.llm import create_llm
from app.agents.tool_runner import ToolRunner
from app.agents.constants import LangGraphEvent, StreamEventType
import logging

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    type: StreamEventType
    data: str | dict


class BaseAgent:
    """Base agent with graph building, streaming modes, and tool execution."""
    
    def __init__(self, system_prompt: str, tools: list, state_class: type):
        self._prompt = system_prompt
        self._tools = tools
        self._state_class = state_class
        self._llm = create_llm().bind_tools(tools)
        self._tool_runner = ToolRunner(tools)
        self._graph = self._build_graph()
    
    def _build_graph(self):
        builder = StateGraph(self._state_class)
        builder.add_node("llm", self._call_llm)
        builder.add_node("tools", self._tool_runner.run)
        builder.add_edge(START, "llm")
        builder.add_conditional_edges("llm", self._route)
        builder.add_edge("tools", "llm")
        return builder.compile(checkpointer=InMemorySaver())
    
    async def _call_llm(self, state):
        messages = [SystemMessage(content=self._prompt)] + list(state["messages"])
        user_input = state["messages"][-1].content if state["messages"] else ""
        logger.info(f"LLM invoked: {len(messages)} messages, user_input={user_input[:100]}...")
        
        response = await self._llm.ainvoke(messages)
        
        # Log raw response
        logger.info(f"LLM raw response: {response}")
        
        # Log token usage if available
        usage = getattr(response, "usage_metadata", None)
        if usage:
            logger.info(f"LLM usage: input_tokens={usage.get('input_tokens', 0)}, output_tokens={usage.get('output_tokens', 0)}, total={usage.get('total_tokens', 0)}")
        
        return {"messages": [response]}
    
    def _route(self, state) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END
    
    async def stream_text(self, message: str, thread_id: str) -> AsyncGenerator[str, None]:
        """Stream only text chunks."""
        async for event in self._stream_all(message, thread_id):
            if event.type == StreamEventType.TEXT:
                yield event.data
    
    async def stream_events(self, message: str, thread_id: str) -> AsyncGenerator[StreamEvent, None]:
        """Stream all events (text, tools, llm states)."""
        async for event in self._stream_all(message, thread_id):
            yield event
    
    async def run(self, message: str, thread_id: str) -> str:
        """Run and return final response only."""
        config = {"configurable": {"thread_id": thread_id}}
        result = await self._graph.ainvoke({"messages": [HumanMessage(content=message)]}, config)
        return str(result["messages"][-1].content)
    
    async def _stream_all(self, message: str, thread_id: str) -> AsyncGenerator[StreamEvent, None]:
        config = {"configurable": {"thread_id": thread_id}}
        async for event in self._graph.astream_events(
            {"messages": [HumanMessage(content=message)]}, config=config, version="v2"
        ):
            kind = event.get("event")
            name = event.get("name", "")
            
            # Log all events for debugging
            if kind not in ["on_chat_model_stream"]:
                logger.debug(f"Event: {kind}, name={name}")
            
            if kind == LangGraphEvent.CHAT_MODEL_START:
                yield StreamEvent(StreamEventType.LLM_START, {})
            elif kind == LangGraphEvent.CHAT_MODEL_END:
                yield StreamEvent(StreamEventType.LLM_END, {})
            elif kind == LangGraphEvent.CHAT_MODEL_STREAM:
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content"):
                    text = self._extract_text(chunk.content)
                    if text:
                        yield StreamEvent(StreamEventType.TEXT, text)
            elif kind == LangGraphEvent.TOOL_START:
                yield StreamEvent(StreamEventType.TOOL_START, {"name": name})
            elif kind == LangGraphEvent.TOOL_END:
                yield StreamEvent(StreamEventType.TOOL_END, {"name": name})
            # Fallback: detect tool node execution
            elif kind == "on_chain_start" and name == "tools":
                yield StreamEvent(StreamEventType.TOOL_START, {"name": "Fetching data..."})
            elif kind == "on_chain_end" and name == "tools":
                yield StreamEvent(StreamEventType.TOOL_END, {"name": "tools"})
    
    def _extract_text(self, content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content)
        return ""
