"""LLM layer: one door into every model provider.

Why this file exists: the rest of the app should never import OpenAI or
Anthropic directly. If you switch providers, you only change .env.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from research_agent.config import get_settings


def get_chat_model(temperature: float = 0.2) -> BaseChatModel:
    settings = get_settings()
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
        from langchain_ollama import ChatOllama

        return ChatOllama(model=settings.ollama_model, temperature=temperature)

    raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use openai, anthropic, or ollama.")
