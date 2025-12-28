from enum import Enum
from typing import Any
from langchain_core.language_models import BaseChatModel


class LLMProvider(str, Enum):
    BEDROCK = "bedrock"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"


class LLMModel(str, Enum):
    # Anthropic (direct API)
    CLAUDE_SONNET_4 = "claude-sonnet-4-5-20250929"
    CLAUDE_HAIKU_3_5 = "claude-3-5-haiku-20241022"
    CLAUDE_OPUS_3 = "claude-3-opus-20240229"
    
    # Bedrock (Anthropic via AWS)
    BEDROCK_CLAUDE_SONNET_3_5 = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    BEDROCK_CLAUDE_HAIKU_3_5 = "anthropic.claude-3-5-haiku-20241022-v1:0"
    
    # OpenAI
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_O1 = "o1"
    GPT_O1_MINI = "o1-mini"
    
    # Google
    GEMINI_2_FLASH = "gemini-2.0-flash"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"


LLM_MODEL_PROVIDERS: dict[LLMModel, LLMProvider] = {
    # Anthropic
    LLMModel.CLAUDE_SONNET_4: LLMProvider.ANTHROPIC,
    LLMModel.CLAUDE_HAIKU_3_5: LLMProvider.ANTHROPIC,
    LLMModel.CLAUDE_OPUS_3: LLMProvider.ANTHROPIC,
    # Bedrock
    LLMModel.BEDROCK_CLAUDE_SONNET_3_5: LLMProvider.BEDROCK,
    LLMModel.BEDROCK_CLAUDE_HAIKU_3_5: LLMProvider.BEDROCK,
    # OpenAI
    LLMModel.GPT_4O: LLMProvider.OPENAI,
    LLMModel.GPT_4O_MINI: LLMProvider.OPENAI,
    LLMModel.GPT_O1: LLMProvider.OPENAI,
    LLMModel.GPT_O1_MINI: LLMProvider.OPENAI,
    # Google
    LLMModel.GEMINI_2_FLASH: LLMProvider.GOOGLE,
    LLMModel.GEMINI_2_5_PRO: LLMProvider.GOOGLE,
    LLMModel.GEMINI_2_5_FLASH: LLMProvider.GOOGLE,
}


LLM_DEFAULT_MAX_RETRIES = 2
LLM_DEFAULT_TIMEOUT = 60


def get_llm_provider(model: LLMModel) -> LLMProvider:
    return LLM_MODEL_PROVIDERS[model]


def _get_provider_config(provider: LLMProvider) -> dict[str, Any]:
    from app.core.settings import settings
    
    if provider == LLMProvider.BEDROCK:
        return {"region_name": settings.aws_region}
    
    if provider == LLMProvider.ANTHROPIC:
        return {"anthropic_api_key": settings.anthropic_api_key}
    
    if provider == LLMProvider.OPENAI:
        return {"openai_api_key": settings.openai_api_key}
    
    if provider == LLMProvider.GOOGLE:
        return {"google_api_key": settings.google_api_key}
    
    return {}


class LLMFactory:
    @classmethod
    def create(
        cls,
        provider: LLMProvider,
        model_id: str | LLMModel,
        max_retries: int = LLM_DEFAULT_MAX_RETRIES,
        timeout: int | None = LLM_DEFAULT_TIMEOUT,
        **kwargs: Any,
    ) -> BaseChatModel:
        model_str = model_id.value if isinstance(model_id, LLMModel) else model_id
        
        provider_config = _get_provider_config(provider)
        
        common_kwargs = {
            "max_retries": max_retries,
            "timeout": timeout,
            **provider_config,
            **kwargs,
        }
        
        if provider == LLMProvider.BEDROCK:
            from langchain_aws import ChatBedrockConverse
            return ChatBedrockConverse(model_id=model_str, **common_kwargs)

        if provider == LLMProvider.ANTHROPIC:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=model_str, **common_kwargs)

        if provider == LLMProvider.OPENAI:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model_str, **common_kwargs)

        if provider == LLMProvider.GOOGLE:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=model_str, **common_kwargs)

        raise ValueError(f"Unsupported provider: {provider}")

    @classmethod
    def create_from_model(cls, llm_model: LLMModel, **kwargs: Any) -> BaseChatModel:
        return cls.create(get_llm_provider(llm_model), llm_model, **kwargs)

    @classmethod
    def create_from_string(cls, model_spec: str, **kwargs: Any) -> BaseChatModel:
        if ":" not in model_spec:
            raise ValueError(f"Invalid model spec: {model_spec}. Use 'provider:model_id' format.")
        
        provider_str, model_id = model_spec.split(":", 1)
        provider = LLMProvider(provider_str.lower())
        return cls.create(provider, model_id, **kwargs)

    @classmethod
    def create_with_fallback(
        cls,
        primary: tuple[LLMProvider, LLMModel],
        fallbacks: list[tuple[LLMProvider, LLMModel]],
        **kwargs: Any,
    ) -> BaseChatModel:
        primary_llm = cls.create(primary[0], primary[1], **kwargs)
        
        fallback_llms = [
            cls.create(provider, model, **kwargs)
            for provider, model in fallbacks
        ]
        
        return primary_llm.with_fallbacks(fallback_llms)
