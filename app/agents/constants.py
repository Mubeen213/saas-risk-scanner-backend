from enum import StrEnum


class LangGraphEvent(StrEnum):
    """
    LangGraph astream_events event types (v2).
    
    Sequence for chat with tools:
    
    1. CHAT_MODEL_START    → LLM begins
    2. CHAT_MODEL_STREAM   → Text chunks (multiple)
    3. CHAT_MODEL_END      → LLM done, may have tool_calls
    4. TOOL_START          → Tool begins
    5. TOOL_END            → Tool done with output
    6. CHAT_MODEL_START    → LLM processes tool result
    7. CHAT_MODEL_STREAM   → Final response chunks
    8. CHAT_MODEL_END      → Done
    """
    CHAT_MODEL_START = "on_chat_model_start"   # data: {}
    CHAT_MODEL_END = "on_chat_model_end"       # data: {"output": AIMessage}
    CHAT_MODEL_STREAM = "on_chat_model_stream" # data: {"chunk": AIMessageChunk}
    TOOL_START = "on_tool_start"               # name: str, data: {"input": dict}
    TOOL_END = "on_tool_end"                   # name: str, data: {"output": Any}


class StreamEventType(StrEnum):
    """
    Simplified events from BaseAgent.stream_events().
    
    Formats:
    - TEXT:       StreamEvent(type=TEXT, data="chunk")
    - LLM_START:  StreamEvent(type=LLM_START, data={})
    - LLM_END:    StreamEvent(type=LLM_END, data={})
    - TOOL_START: StreamEvent(type=TOOL_START, data={"name": str})
    - TOOL_END:   StreamEvent(type=TOOL_END, data={"name": str, "output": Any})
    """
    TEXT = "text"
    LLM_START = "llm_start"
    LLM_END = "llm_end"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
