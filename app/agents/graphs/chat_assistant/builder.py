from langgraph.graph import StateGraph, START, END

from app.agents.graphs.base_graph import BaseGraphBuilder
from app.agents.graphs.chat_assistant.state import ChatAssistantState
from app.agents.graphs.chat_assistant.prompts import SYSTEM_PROMPT
from app.agents.nodes.llm_node import create_model_node
from app.agents.nodes.tool_executor import InstrumentedToolExecutor


class ChatAssistantGraphBuilder(BaseGraphBuilder):
    def __init__(self, model, tools: list, checkpointer=None):
        super().__init__(checkpointer)
        self._model = model.bind_tools(tools)
        self._tools = tools
        self._tool_executor = InstrumentedToolExecutor(tools, "chat_assistant")

    def _get_state_class(self):
        return ChatAssistantState

    def _add_nodes(self, builder: StateGraph):
        builder.add_node("reason", create_model_node(self._model, SYSTEM_PROMPT, "chat_assistant"))
        builder.add_node("execute_tools", self._tool_executor.invoke)

    def _add_edges(self, builder: StateGraph):
        builder.add_edge(START, "reason")
        builder.add_conditional_edges("reason", self._route_after_reason)
        builder.add_edge("execute_tools", "reason")

    def _route_after_reason(self, state: ChatAssistantState) -> str:
        messages = state.get("messages", [])
        if not messages:
            return END
        
        last = messages[-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "execute_tools"
        return END
