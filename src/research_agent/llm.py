"""LLM layer: one door into every model provider.

Why this file exists: the rest of the app should never import OpenAI or
Anthropic directly. If you switch providers, you only change .env.

Supported LLM_PROVIDER values (default openai):
  openai | anthropic | ollama | azure | bedrock

Vertex AI is not wired here — keep this factory small. Tests never call a
cloud account; they only check that missing config fails loudly.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from research_agent.config import Settings, get_settings

KNOWN_PROVIDERS = ("openai", "anthropic", "ollama", "azure", "bedrock")


def get_chat_model(
    temperature: float = 0.2,
    settings: Settings | None = None,
) -> BaseChatModel:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower().strip()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if not settings.openai_api_key:
            raise RuntimeError("Set OPENAI_API_KEY or switch LLM_PROVIDER.")
        return ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=temperature,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not settings.anthropic_api_key:
            raise RuntimeError("Set ANTHROPIC_API_KEY or switch LLM_PROVIDER.")
        return ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            temperature=temperature,
        )

    if provider == "ollama":
        import os

        from langchain_ollama import ChatOllama

        if settings.ollama_api_key:
            os.environ["OLLAMA_API_KEY"] = settings.ollama_api_key
        kwargs: dict = {
            "model": settings.ollama_model,
            "temperature": temperature,
        }
        if settings.ollama_host:
            kwargs["base_url"] = settings.ollama_host
        return ChatOllama(**kwargs)

    if provider == "azure":
        from langchain_openai import AzureChatOpenAI

        if not settings.azure_openai_api_key:
            raise RuntimeError("Set AZURE_OPENAI_API_KEY or switch LLM_PROVIDER.")
        if not settings.azure_openai_endpoint:
            raise RuntimeError("Set AZURE_OPENAI_ENDPOINT.")
        if not settings.azure_openai_deployment:
            raise RuntimeError("Set AZURE_OPENAI_DEPLOYMENT.")
        return AzureChatOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
            temperature=temperature,
        )

    if provider == "bedrock":
        from langchain_aws import ChatBedrockConverse

        if not settings.bedrock_model_id:
            raise RuntimeError("Set BEDROCK_MODEL_ID or switch LLM_PROVIDER.")
        # AWS keys stay in the usual env vars (AWS_ACCESS_KEY_ID, etc.).
        # This factory does not train models or call SageMaker.
        kwargs: dict = {
            "model": settings.bedrock_model_id,
            "temperature": temperature,
        }
        if settings.aws_region:
            kwargs["region_name"] = settings.aws_region
        return ChatBedrockConverse(**kwargs)

    raise ValueError(
        f"Unknown LLM_PROVIDER: {provider}. Use {', '.join(KNOWN_PROVIDERS)}."
    )
