import json
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.settings import settings
import logging

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 2


def create_llm(max_retries: int = DEFAULT_MAX_RETRIES) -> BaseChatModel:
    """Create LLM based on settings. Auto-selects provider and API key."""
    provider = settings.llm_provider
    model_id = settings.llm_id
    
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_id, google_api_key=settings.google_api_key, max_retries=max_retries
        )
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_id, anthropic_api_key=settings.anthropic_api_key, max_retries=max_retries
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_id, openai_api_key=settings.openai_api_key, max_retries=max_retries
        )
    if provider == "bedrock":
        from langchain_aws import ChatBedrockConverse
        return ChatBedrockConverse(
            model_id=model_id, region_name=settings.aws_region, max_retries=max_retries
        )
    raise ValueError(f"Unknown provider: {provider}")


class StructuredLLM:
    """Reusable class to call LLM and parse into Pydantic model."""
    
    def __init__(self, llm: BaseChatModel | None = None):
        self._llm = llm or create_llm()

    async def call(self, prompt: str, input: str | dict, schema: Type[T]) -> T:
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=input if isinstance(input, str) else json.dumps(input)),
        ]
        logger.info(f"StructuredLLM: {schema.__name__}")
        response = await self._llm.ainvoke(messages)
        try:
            return schema.model_validate(json.loads(response.content))
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Failed to parse {schema.__name__}: {e}")
