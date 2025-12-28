from abc import ABC, abstractmethod
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver


class BaseGraphBuilder(ABC):
    def __init__(self, checkpointer: InMemorySaver | None = None):
        self._checkpointer = checkpointer or InMemorySaver()
        self._compiled = None

    @abstractmethod
    def _get_state_class(self) -> type:
        pass

    @abstractmethod
    def _add_nodes(self, builder: StateGraph) -> None:
        pass

    @abstractmethod
    def _add_edges(self, builder: StateGraph) -> None:
        pass

    def build(self):
        builder = StateGraph(self._get_state_class())
        self._add_nodes(builder)
        self._add_edges(builder)
        self._compiled = builder.compile(checkpointer=self._checkpointer)
        return self._compiled

    @property
    def graph(self):
        if not self._compiled:
            self.build()
        return self._compiled
