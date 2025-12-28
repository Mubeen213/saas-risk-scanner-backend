from typing import Type, TypeVar
from pydantic import BaseModel
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.core.logging import AgentLogger


T = TypeVar("T", bound=BaseModel)


class StructuredLLM:
    def __init__(self, model: BaseChatModel):
        self._model = model

    def with_schema(self, schema: Type[T]) -> "BoundStructuredLLM[T]":
        return BoundStructuredLLM(self._model, schema)


class BoundStructuredLLM[T]:
    def __init__(self, model: BaseChatModel, schema: Type[T]):
        self._structured = model.with_structured_output(schema)
        self._schema = schema
        self._logger = AgentLogger("structured_model")

    async def invoke(
        self,
        *,
        prompt: str,
        input_data: str | dict,
    ) -> T:
        content = input_data if isinstance(input_data, str) else str(input_data)
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=content),
        ]
        
        self._logger.log_llm_start(
            prompt_preview=prompt[:100],
            message_count=len(messages),
        )
        
        result = await self._structured.ainvoke(messages)
        
        self._logger.log_structured_output(
            schema_name=self._schema.__name__,
            fields=list(result.model_dump().keys()),
        )
        
        return result

    def invoke_sync(
        self,
        *,
        prompt: str,
        input_data: str | dict,
    ) -> T:
        content = input_data if isinstance(input_data, str) else str(input_data)
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=content),
        ]
        
        self._logger.log_llm_start(
            prompt_preview=prompt[:100],
            message_count=len(messages),
        )
        
        result = self._structured.invoke(messages)
        
        self._logger.log_structured_output(
            schema_name=self._schema.__name__,
            fields=list(result.model_dump().keys()),
        )
        
        return result
