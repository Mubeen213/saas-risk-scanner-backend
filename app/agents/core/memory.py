from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import RemoveMessage, HumanMessage


def create_checkpointer() -> InMemorySaver:
    return InMemorySaver()


async def trim_old_messages(
    graph,
    config: dict,
    max_human_messages: int = 10,
    keep_recent: int = 4,
) -> list:
    state = await graph.aget_state(config)
    if not state or not state.values.get("messages"):
        return []

    messages = state.values["messages"]
    human_count = sum(1 for m in messages if isinstance(m, HumanMessage))

    if human_count <= max_human_messages:
        return []

    return [
        RemoveMessage(id=m.id)
        for m in messages[:-keep_recent]
        if hasattr(m, "id")
    ]
