from functools import lru_cache

from app.agents.core.llm_factory import LLMFactory, LLMProvider
from app.agents.core.memory import create_checkpointer
from app.agents.core.interrupt_handler import InterruptHandler
from app.agents.graphs.chat_assistant.builder import ChatAssistantGraphBuilder
from app.agents.services.executor import AgentExecutor
from app.agents.tools.workspace import get_workspace_stats, list_apps, get_app_details
from app.core.settings import settings


WORKSPACE_TOOLS = [get_workspace_stats, list_apps, get_app_details]


@lru_cache
def get_model():
    return LLMFactory.create(
        LLMProvider(settings.llm_provider),
        settings.llm_id,
    )


@lru_cache
def get_chat_assistant_graph():
    model = get_model()
    checkpointer = create_checkpointer()
    builder = ChatAssistantGraphBuilder(model, WORKSPACE_TOOLS, checkpointer)
    return builder.build()


def get_agent_executor() -> AgentExecutor:
    graph = get_chat_assistant_graph()
    return AgentExecutor(graph)


def get_interrupt_handler() -> InterruptHandler:
    graph = get_chat_assistant_graph()
    return InterruptHandler(graph)


def get_chat_service():
    from app.agents.services.chat_service import ChatService
    executor = get_agent_executor()
    return ChatService(executor)
