from app.agents.base_agent import BaseAgent
from app.agents.prompts import CHAT_ASSISTANT_PROMPT
from app.agents.tools.workspace import get_workspace_stats, list_apps, get_app_details
from app.agents.state import AgentState


TOOLS = [get_workspace_stats, list_apps, get_app_details]


def create_chat_agent() -> BaseAgent:
    return BaseAgent(
        system_prompt=CHAT_ASSISTANT_PROMPT,
        tools=TOOLS,
        state_class=AgentState,
    )


_agent = None


def get_chat_agent() -> BaseAgent:
    global _agent
    if not _agent:
        _agent = create_chat_agent()
    return _agent
