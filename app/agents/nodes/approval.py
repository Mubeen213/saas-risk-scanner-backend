from typing import Literal
from langgraph.types import interrupt, Command

from app.agents.core.logging import AgentLogger


logger = AgentLogger("approval")


def create_approval_node(action_key: str):
    def node(state: dict) -> Command[Literal["proceed", "cancel"]]:
        action_details = state.get(action_key, {})
        
        payload = {
            "type": "approval_required",
            "action": action_key,
            "details": action_details,
            "message": "Approve this action?",
        }
        
        logger.log_interrupt("approval_requested", payload)
        
        response = interrupt(payload)
        
        logger.log_interrupt(
            "approval_response",
            {"approved": bool(response), "action": action_key},
        )
        
        if response:
            return Command(goto="proceed")
        return Command(goto="cancel")
    
    return node
