from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.agents.core.logging import AgentLogger


def create_model_node(model, system_prompt: str, agent_name: str = "agent"):
    logger = AgentLogger(agent_name)
    
    async def node(state: dict, config: RunnableConfig) -> dict:
        messages = list(state.get("messages", []))
        
        messages.insert(0, SystemMessage(content=system_prompt))
        
        if summary := state.get("summary"):
            messages.insert(1, SystemMessage(content=f"Conversation context: {summary}"))
        
        last_human = next(
            (m.content[:100] for m in reversed(messages) if hasattr(m, "content")),
            ""
        )
        logger.log_llm_start(
            prompt_preview=last_human,
            message_count=len(messages),
        )
        
        try:
            response = await model.ainvoke(messages, config=config)
            
            usage = getattr(response, "usage_metadata", None) or {}
            logger.log_llm_end(
                response_preview=str(response.content)[:150],
                usage={
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            )
            
            return {"messages": [response]}
        except Exception as e:
            logger.log_error("llm_invocation_failed", str(e))
            return {"messages": [AIMessage(content="I encountered an issue. Please try again.")]}
    
    return node
